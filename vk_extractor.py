"""
VK API wrapper

For more information on this file, see https://vk.com/dev/first_guide

"""

import requests
import vk_api
from .decorators import force
from .exceptions import UserIdError, ApiRequestError
from . import settings


@force
def send_vk_request(method_name, **kwargs):
    """Return vk api response

    takes a method name and arguments, sends a request, and returns a response
    read https://vk.com/dev/manuals

    """

    response = requests.get(
        f'https://api.vk.com/method/{method_name}',
        params=kwargs
    ).json()

    if 'response' in response:
        return response['response']
    elif 'error' in response:
        error = response['error']
        if error.get('error_code') == 6:
            raise TimeoutError('Слишком много запросов в секунду')
        elif error.get('error_code') == 113:
            raise UserIdError('Неверный идентификатор пользователя ВК')
        else:
            raise ApiRequestError(error.get('error_msg'))
    else:
        raise ConnectionError('Не удалось установить соединение с VK API, '
                              'проверьте корректность введенных данных')


def get_users_info(token, ids):
    """Return a response from vk api users.get

    :param token: access token
    :param ids: users ids
    :return: dict with users info

    """

    args = {
        'user_ids': ids,
        'fields': 'city,bdate,connections,photo_200',
        'access_token': token,
        'v': settings.api_v
    }

    return send_vk_request('users.get', **args)[0]


def get_friends_list(token, uid):
    """Return a response from vk api friends.get

    :param token: access token
    :param uid: users id
    :return: dict with friends ids

    example: {'count' : 2, 'items': [213412, 124124]}

    """
    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()

    try:
        friends = vk.friends.get(user_id=uid, fields='bdate, city, photo_200', v=settings.api_v)
    except vk_api.ApiError as error:
        if error.code == 6:
            raise TimeoutError('Слишком много запросов в секунду')
        elif error.code == 113:
            raise UserIdError('Неверный идентификатор пользователя ВК')
        else:
            raise ApiRequestError(error)
    return friends


def get_mutual_friends(token, source_uid, target_uids):
    """Returns mutual friends of the given user and target users

    :param token: access token
    :param source_uid: source user id
    :param target_uids: list of users to find mutual friends
    :return: dictionary with pairs of user id - list of mutual friends ids

    example: {friend id: [mutual id 1, mutual id 2, ...]}

    """
    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()

    uids_batches = [target_uids[i:i + 100] for i in range(0, len(target_uids), 100)]
    friends_bathes = {}
    with vk_api.VkRequestsPool(vk_session) as pool:
        for i in range(len(uids_batches)):
            friends_bathes[i] = pool.method('friends.getMutual', {
                'source_uid': source_uid,
                'target_uids': uids_batches[i],
                'v': settings.api_v
            })
    mutual_friends = {}
    for key, value in friends_bathes.items():
        try:
            friends_bathes[key] = value.result
            [mutual_friends.update({int(friend['id']): friend['common_friends']}) for friend in friends_bathes[key]]
        except vk_api.VkRequestsPoolException as error:
            raise ApiRequestError(error)
    return mutual_friends


def create_incidence_list(uid, friends_ids, _mutual_friends):
    mutual_friends = _mutual_friends.copy()

    incidence_list = {}
    mutual_friends.update({uid: friends_ids})
    for friend in mutual_friends:
        incidence_list.update({friend: {}})
        for mutual in mutual_friends[friend]:
            incidence_list[friend].update({mutual: 0})
        incidence_list[friend].update({uid: 0})

    return incidence_list


def send_vk_requests_one_param_pool(token, method, key, batches, **default_values):
    vk_session = vk_api.VkApi(token=token)
    responses = {}
    for batch in batches:
        response, errors = vk_api.vk_request_one_param_pool(
                    vk_session,
                    method,
                    key=key,
                    values=batch,
                    default_values=default_values
                    )
        responses.update(response)
    return responses


def get_friends_gifts(token, uid, _active_friends_ids, friends_ids, mutual_friends):
    active_friends_ids = _active_friends_ids.copy()

    friends_gifts = create_incidence_list(uid, friends_ids, mutual_friends)
    active_friends_ids.append(uid)
    uids_batches = [active_friends_ids[i:i + 25] for i in range(0, len(active_friends_ids), 25)]

    gifts = send_vk_requests_one_param_pool(token, 'gifts.get', 'user_id', uids_batches, 
            count=1000, v=settings.api_v)
    for uid in gifts:
        for gift in gifts[uid]['items']:
            if uid in friends_gifts and gift['from_id'] in friends_gifts[uid]:
                friends_gifts[uid][gift['from_id']] += 1
    return friends_gifts


def get_friends_likes(token, uid, _active_friends_ids, friends_ids, mutual_friends):
    vk_session = vk_api.VkApi(token=token)
    active_friends_ids = _active_friends_ids.copy()

    friends_likes = create_incidence_list(uid, friends_ids, mutual_friends)
    active_friends_ids.append(uid)
    uids_batches = [active_friends_ids[i:i + 25] for i in range(0, len(active_friends_ids), 25)]
    
    walls = send_vk_requests_one_param_pool(token, 'wall.get', 'owner_id', uids_batches, 
            filter='owner', count=25, v=settings.api_v)
    for friend_id in walls:
        wall = walls[friend_id]['items']
        posts_ids = [wall[i]['id'] for i in range(len(wall))]
        likes_of_posts, errors_likes = vk_api.vk_request_one_param_pool(
            vk_session,
            'likes.getList',
            key='item_id',
            values=posts_ids,
            default_values={'owner_id': friend_id, 'type': 'post', 'filter': 'likes', 'count': 100, 'v': settings.api_v}
            )
        for post_id in likes_of_posts:
            for like_uid in likes_of_posts[post_id]['items']:
                if friend_id in friends_likes and like_uid in friends_likes[friend_id]:
                    friends_likes[friend_id][like_uid] += 1
    return friends_likes