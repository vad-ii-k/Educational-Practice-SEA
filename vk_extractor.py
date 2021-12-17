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
    :param uid: user id
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
    """Class for collecting statistics about the interaction of friends"""

    def __init__(self, token, uid, friends_ids, active_friends_ids):
        """
        :param token: access token
        :param uid: user id
        :param friends_ids: list of user's friends IDs
        :param active_friends_ids: list of non-deactivated and non-closed user's friends IDs
        :param mutual_friends: dictionary of IDs of the user's friends and friends common with him and a friend
        """
        
        self.token = token
        self.uid = uid
        self.friends_ids = copy.deepcopy(friends_ids)
        self.friends_ids.append(uid)
        self.active_friends_ids = copy.deepcopy(active_friends_ids)
        self.active_friends_ids.append(uid)
        self.uids_batches = self._create_uids_batches()
        self.walls = self._get_walls()

    def _filling_stats(self, responses, stats, friend_id):
        """Method for filling in dict of statistics on response from the API"""

        if friend_id == 0:
            for user_id in responses:
                if user_id in self.friends_ids:
                    stats.update({user_id: {}})
                    for item in responses[user_id]['items']:
                        item_from_id = item['from_id']
                        if item_from_id in self.friends_ids:
                            if item_from_id in stats[user_id]:
                                stats[user_id][item_from_id] += 1
                            else:
                                stats[user_id].update({item_from_id: 1})
        else:
            if friend_id not in stats:
                stats.update({friend_id: {}})
            for response_id in responses:
                for item in responses[response_id]['items']:
                    item_from_id = item if isinstance(item, int) else item['from_id']
                    if item_from_id in self.friends_ids:
                        if item_from_id in stats[friend_id]:
                            stats[friend_id][item_from_id] += 1
                        else:
                            stats[friend_id].update({item_from_id: 1})

    def _create_uids_batches(self):
        """Method for dividing the active_friends_ids list into parts of 25 in each for using pool requests
        :return: list, each of elements of which, with the possible exception of the last one, contains IDs of 25 active friends of user
        example: [[active_friend_id1, ..., active_friend_id25], ..., [active_friend_id100, ..., active_friend_id115]]
        """

        uids_batches = [self.active_friends_ids[i:i + 25] for i in range(0, len(self.active_friends_ids), 25)]
        return uids_batches

    def _send_vk_requests_one_param_pool(self, method, key, **default_values):
        """Wrapper over vk_request_one_param_pool to get information for all friends at once
            read https://vk-api.readthedocs.io/en/latest/requests_pool.html
        param method: VK API method
        param key: key for request dict, is name of one of parameters for request
        """

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

    def get_gifts(self):
        """Method for collecting data about friends' gifts
        :return: completed dict of incidents
        example: {uid : {{friend_id1: weight_1}, {friend_id2: weight_2}, ..., {uid: weight_3}}, friend_id2 : {{friend_id3: weight_4}, ..., {uid: weight_5}}, ...}
        """

        gifts = self._send_vk_requests_one_param_pool('gifts.get', 'user_id', 
                count=1000, v=settings.api_v)
        friends_gifts = {}
        self._filling_stats(gifts, friends_gifts, 0)
        return friends_gifts

    def _get_walls(self):
        """Method for collecting data about friends' walls for further collection of statistics about the last 25 posts
        :return: dict of usual wall.get method responses, where key is owner_id and value is response
        """

        walls = self._send_vk_requests_one_param_pool('wall.get', 'owner_id', 
                filter='owner', count=25, v=settings.api_v)
        return walls

    def get_likes(self):
        """Method for collecting data about friends' likes
        :return: completed dict of incidents
        example: {uid : {{friend_id1: weight_1}, {friend_id2: weight_2}, ..., {uid: weight_3}}, friend_id2 : {{friend_id3: weight_4}, ..., {uid: weight_5}}, ...}
        """

        vk_session = vk_api.VkApi(token=self.token)

        friends_likes = {}
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
                self._filling_stats(likes_of_posts, friends_likes, friend_id)
        return friends_likes

    def get_comments(self):
        """Method for collecting data about friends' comments
        :return: completed dict of incidents
        example: {uid : {{friend_id1: weight_1}, {friend_id2: weight_2}, ..., {uid: weight_3}}, friend_id2 : {{friend_id3: weight_4}, ..., {uid: weight_5}}, ...}
        """

        vk_session = vk_api.VkApi(token=self.token)

        friends_comments = {}
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
                self._filling_stats(comments_of_posts, friends_comments, friend_id)
        return friends_comments