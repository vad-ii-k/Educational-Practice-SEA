"""
VK API wrapper

For more information on this file, see https://vk.com/dev/first_guide

"""

import requests
import vk_api
from .decorators import force
from .exceptions import UserIdError, ApiRequestError
from . import settings
import copy


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


class FriendsStatistics:

    def __init__(self, token, uid, friends_ids, active_friends_ids, mutual_friends):
        self.token = token
        self.uid = uid
        self.friends_ids = friends_ids
        self.active_friends_ids = active_friends_ids
        self.mutual_friends = mutual_friends
        self.incidence_list = self._create_incidence_list()
        self.uids_batches = self._create_uids_batches()
        self.walls = self._get_walls()
        self.gifts = self._get_gifts()
        self.likes = self._get_likes()
        self.comments = self._get_comments()

    def _create_incidence_list(self):
        mutual_friends = copy.deepcopy(self.mutual_friends)

        incidence_list = {}
        mutual_friends.update({self.uid: self.friends_ids})
        for friend in mutual_friends:
            incidence_list.update({friend: {}})
            for mutual in mutual_friends[friend]:
                incidence_list[friend].update({mutual: 0})
            incidence_list[friend].update({self.uid: 0})
        return incidence_list

    def _create_uids_batches(self):
        active_friends_ids = copy.deepcopy(self.active_friends_ids)
        active_friends_ids.append(self.uid)
        uids_batches = [active_friends_ids[i:i + 25] for i in range(0, len(active_friends_ids), 25)]
        return uids_batches

    def _send_vk_requests_one_param_pool(self, method, key, **default_values):
        vk_session = vk_api.VkApi(token=self.token)
        responses = {}
        for batch in self.uids_batches:
            response, errors = vk_api.vk_request_one_param_pool(
                        vk_session,
                        method,
                        key=key,
                        values=batch,
                        default_values=default_values
                        )
            responses.update(response)
        return responses

    def _get_gifts(self):
        active_friends_ids = copy.deepcopy(self.active_friends_ids)

        gifts = self._send_vk_requests_one_param_pool('gifts.get', 'user_id', 
                count=1000, v=settings.api_v)
        friends_gifts = copy.deepcopy(self.incidence_list)
        for friend_id in gifts:
            for gift in gifts[friend_id]['items']:
                if friend_id in friends_gifts and gift['from_id'] in friends_gifts[friend_id]:
                    friends_gifts[friend_id][gift['from_id']] += 1
        return friends_gifts

    def _get_walls(self):
        walls = self._send_vk_requests_one_param_pool('wall.get', 'owner_id', 
                filter='owner', count=25, v=settings.api_v)
        return walls

    def _get_likes(self):
        vk_session = vk_api.VkApi(token=self.token)

        friends_likes = copy.deepcopy(self.incidence_list)
        for friend_id in self.walls:
            wall = self.walls[friend_id]['items']
            posts_ids = [wall[i]['id'] for i in range(len(wall))]
            if len(posts_ids) > 0:
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

    def _get_comments(self):
        vk_session = vk_api.VkApi(token=self.token)

        friends_comments = copy.deepcopy(self.incidence_list)
        for friend_id in self.walls:
            wall = self.walls[friend_id]['items']
            posts_ids = [wall[i]['id'] for i in range(len(wall))]
            if len(posts_ids) > 0:
                comments_of_posts, errors_comments = vk_api.vk_request_one_param_pool(
                    vk_session,
                    'wall.getComments',
                    key='post_id',
                    values=posts_ids,
                    default_values={'owner_id': friend_id,  'count': 100, 'preview_length': 1, 'v': settings.api_v}
                    )
                for post_id in comments_of_posts:
                    for comment in comments_of_posts[post_id]['items']:
                        if friend_id in friends_comments and comment['from_id'] in friends_comments[friend_id]:
                            friends_comments[friend_id][comment['from_id']] += 1
        return friends_comments