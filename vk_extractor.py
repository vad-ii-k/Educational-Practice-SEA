"""
VK API wrapper

For more information on this file, see https://vk.com/dev/first_guide

"""

import requests
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


def get_friends_list(token, id_):
    """Return a response from vk api friends.get

    :param token: access token
    :param id_: users id
    :return: dict with friends ids

    example: {'count' : 2, 'items': [213412, 124124]}

    """

    args = {
        'user_id': id_,
        'fields': 'bdate, city, photo_200',
        'access_token': token,
        'v': settings.api_v,
    }

    return send_vk_request('friends.get', **args)


def get_mutual_friends(token, source_uid, target_uids):
    """Returns mutual friends of the given user and target users

    :param token: access token
    :param source_uid: source user
    :param target_uids: list of users to find mutual friends
    :return: dictionary with pairs of user id - list of mutual friends ids

    """

    mutual_friends = {}
    uids_batches = [target_uids[i:i + 25] for i in range(0, len(target_uids), 25)]
    for batch in uids_batches:
        # Формируем code (параметр execute)
        code = 'return {'
        for uid in batch:
            code = '%s%s' % (
                code,
                '"%s": API.friends.getMutual({"source_uid":%s, "target_uid":%s}),' % (
                    uid,
                    source_uid,
                    uid
                )
            )
        code = '%s%s' % (code, '};')
        args = {
            'code': code,
            'access_token': token,
            'v': settings.api_v
        }
        for key, value in send_vk_request('execute', **args).items():
            mutual_friends.update({int(key): value})
    return mutual_friends
