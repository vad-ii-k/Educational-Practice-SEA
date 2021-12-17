"""Creating context for display at user request"""
from .exceptions import InvalidTokenError
from .extractors.exceptions import UserIdError, ApiRequestError
from .models import VKUser, OKUser
from .tokens.tokens import VKSocialToken, OKSocialToken
from .dbqueries import get_ok_app_secret_key, get_ok_app_key
from .extractors.vk_extractor import get_mutual_friends as vk_get_mutual, FriendsStatistics
from .extractors.ok_extractor import get_mutual_friends as ok_get_mutual
from .forms import VKUserForm, OKUserForm
from .profiles_matching.prediction import get_predict
from .friends_graph.visualization import SocialGraph


def get_compare_context(request):
    """Returns context for compare page"""

    vk_user = ok_user = None
    predict = 0

    vk_token = VKSocialToken(request.user)
    ok_token = OKSocialToken(request.user)
    errors = []

    try:
        if 'id_ok' in request.POST and 'id_vk' in request.POST and ok_token.is_valid and vk_token.is_valid:
            vk_form = VKUserForm(request.POST)
            ok_form = OKUserForm(request.POST)
            if vk_form.is_valid() and ok_form.is_valid():
                vk_user = VKUser.get_user(vk_token.token, request.POST.get('id_vk'))
                ok_user = OKUser.get_user(ok_token.token, request.POST.get('id_ok'))
                predict = round(get_predict(vk_user, ok_user) * 100, 1)
            else:
                for es in vk_form.errors.values():
                    errors.extend(error for error in es)
                for es in ok_form.errors.values():
                    errors.extend(error for error in es)
    except UserIdError as e:
        errors.append(e)
    except InvalidTokenError as e:
        errors.append(e)
    except ApiRequestError as e:
        errors.append(e)
    except ConnectionError as e:
        errors.append(e)

    if errors:
        vk_user = ok_user = None
        predict = 0

    context = {
        'ok_form': OKUserForm(),
        'vk_form': VKUserForm(),
        'ok_token': ok_token,
        'vk_token': vk_token,
        'vk_user': vk_user,
        'ok_user': ok_user,
        'predict': predict,
        'error': errors
    }
    return context


def get_analyze_context(request, network):
    """Returns context for search page"""
    if network == 'vk':
        return _get_vk_analyze_context(request)
    elif network == 'ok':
        return _get_ok_analyze_context(request)


def _get_vk_analyze_context(request):
    """Returns VK context for search page"""

    profile = graph = None

    token = VKSocialToken(request.user)
    errors = []

    try:
        if 'id_vk' in request.POST and token.is_valid:
            vk_form = VKUserForm(request.POST)
            if vk_form.is_valid():
                uid = vk_form.cleaned_data.get('id_vk')
                if uid.isdigit():
                    uid = int(uid)
                profile = VKUser.get_user(token.token, uid)
                active_friends_ids = list(friend.get('id') for friend in profile.friends.get('items') if not('deactivated' in friend or friend.get('is_closed')))
                mutual = vk_get_mutual(token.token, profile.id_vk, active_friends_ids)
                friend_uids = list(friend.get('id') for friend in profile.friends.get('items'))
                stats = FriendsStatistics(token.token, profile.id_vk, active_friends_ids, friend_uids)
                if profile.friends_gifts:
                    gifts = profile.friends_gifts
                else:
                    gifts = profile.friends_gifts = stats.get_gifts()
                if profile.friends_likes:
                    likes = profile.friends_likes
                else:
                    likes = profile.friends_likes = stats.get_likes()
                if profile.friends_comments:
                    comments = profile.friends_comments
                else:
                    comments = profile.friends_comments = stats.get_comments()
                profile.save()
                graph = SocialGraph(profile, friend_uids, mutual, gifts, likes, comments)
            else:
                for es in vk_form.errors.values():
                    errors.extend(error for error in es)
    except UserIdError as e:
        errors.append(e)
    except InvalidTokenError as e:
        errors.append(e)
    except ApiRequestError as e:
        errors.append(e)
    except ConnectionError as e:
        errors.append(e)

    context = {
        'vk_form': VKUserForm(),
        'vk_token': token,
        'profile': profile,
        'graph': graph,
        'error': errors
    }
    return context


def _get_ok_analyze_context(request):
    """Returns OK context for search page"""

    profile = graph = None

    token = OKSocialToken(request.user)
    errors = []

    try:
        if 'id_ok' in request.POST and token.is_valid:
            ok_form = OKUserForm(request.POST)
            if ok_form.is_valid():
                uid = ok_form.cleaned_data.get('id_ok')
                profile = OKUser.get_user(token.token, uid)
                friend_uids = list(friend.get('uid') for friend in profile.friends.get('items'))
                mutual = ok_get_mutual(get_ok_app_key(), get_ok_app_secret_key(), token.token, friend_uids)
                graph = SocialGraph(profile, mutual, friend_uids)
            else:
                for es in ok_form.errors.values():
                    errors.extend(error for error in es)
    except UserIdError as e:
        errors.append(e)
    except InvalidTokenError as e:
        errors.append(e)
    except ApiRequestError as e:
        errors.append(e)
    except ConnectionError as e:
        errors.append(e)

    context = {
        'ok_form': OKUserForm(),
        'ok_token': token,
        'profile': profile,
        'graph': graph,
        'error': errors
    }
    return context
