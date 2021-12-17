"""
Data models in the application database

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/db/models/
"""

from django.db import models

from .extractors.exceptions import ApiRequestError, UserIdError
from .extractors import vk_extractor as vk, ok_extractor as ok
from .extractors.attrs_transform import calculate_age, predict_unknown_attribute
from .dbqueries import get_ok_app_key, get_ok_app_secret_key


class UserBase(models.Model):
    """Social network user"""
    uid = models.PositiveBigIntegerField('Идентификатор', default=0, null=True, unique=True)
    is_closed = models.BooleanField('Закрытый аккаунт', default=False, null=False)
    id_ok = models.PositiveBigIntegerField('Адрес страницы OK', null=True, unique=True)
    id_vk = models.PositiveBigIntegerField('Адрес страницы ВК', null=True, unique=True)
    screen_name_vk = models.SlugField('Короткий адрес страницы ВК', max_length=30, null=True, unique=True)
    first_name = models.CharField('Имя пользователя', max_length=50, null=True)
    last_name = models.CharField('Фамилия пользователя', max_length=50, null=True)
    age = models.PositiveSmallIntegerField('Возраст', default=0, null=True)
    restored_age = models.PositiveSmallIntegerField('Восстановленный возраст', default=0, null=True)
    city = models.CharField('Город', max_length=50, null=True)
    restored_city = models.CharField('Восстановленный город', max_length=50, null=True)
    company = models.CharField('Компания', max_length=50, null=True)
    image_url = models.CharField('Аватар', max_length=200, null=True)
    creditworthiness = models.CharField('Кредитоспособность', max_length=200, null=True)
    friends = models.JSONField('Друзья', null=True)
    friends_gifts = models.JSONField('Подарки друзей', null=True)
    friends_likes = models.JSONField('Лайки друзей', null=True)
    friends_comments = models.JSONField('Комментарии друзей', null=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        abstract = True


class VKUser(UserBase):
    """VK user"""

    class Meta:
        verbose_name = 'Пользователь ВК'
        verbose_name_plural = 'Пользователи ВК'

    @classmethod
    def get_user(cls, token, url):
        """Returns model of vk user if it exists, otherwise creates"""
        users = None
        if isinstance(url, int):
            users = cls.objects.filter(id_vk=url)
        elif isinstance(url, str):
            users = cls.objects.filter(screen_name_vk=url)
        if users:
            vk_user = users[0]
        else:
            vk_user = cls.create(token, url)
            if vk_user:
                vk_user.save()
        vk_user._update_friends(token)
        return vk_user

    @classmethod
    def create(cls, token, url):
        usr = vk.get_users_info(token, url)
        id_vk = usr.get('id')
        is_closed = usr.get('is_closed')
        try:
            friends = vk.get_friends_list(token, id_vk)
        except ApiRequestError:
            friends = {'items': [], 'count': 0}
        restored_age = predict_unknown_attribute(friends.get('items'), 'bdate')
        restored_city = predict_unknown_attribute(friends.get('items'), 'city')
        age = calculate_age(usr.get('bdate'))
        city = usr.get('city').get('title') if usr.get('city') else None
        vk_user = cls(
            uid=id_vk,
            is_closed=is_closed,
            friends=friends,
            id_vk=id_vk,
            screen_name_vk=url if isinstance(url, str) else None,
            first_name=usr.get('first_name'),
            last_name=usr.get('last_name'),
            age=age,
            restored_age=restored_age,
            city=city,
            restored_city=restored_city,
            image_url=usr.get('photo_200'),
        )
        return vk_user

    def _update_friends(self, token):
        try:
            self.friends = vk.get_friends_list(token, self.id_vk)
        except ApiRequestError as e:
            print(e)
            self.friends = {'items': [], 'count': 0}
        self.save()


class OKUser(UserBase):
    """OK user"""

    class Meta:
        verbose_name = 'Пользователь ОК'
        verbose_name_plural = 'Пользователи ОК'

    @classmethod
    def get_user(cls, token, uid):
        """Returns model of ok user if it exists, otherwise creates"""
        users = cls.objects.filter(id_ok=uid)
        if users:
            ok_user = users[0]
        else:
            ok_user = cls.create(token, uid)
            if ok_user:
                ok_user.save()
        ok_user._update_friends(token)
        return ok_user

    @classmethod
    def create(cls, token, url):
        app_key = get_ok_app_key()
        app_secret = get_ok_app_secret_key()
        resp = ok.get_users_info(app_key, app_secret, token, [url])
        if not resp:
            raise UserIdError('Неверный идентификатор пользователя ОК')
        usr = resp[0]
        id_ok = usr.get('uid')
        friends = ok.get_user_friends(app_key, app_secret, token, id_ok)
        age = usr.get('age')
        restored_age = predict_unknown_attribute(friends.get('items'), 'age')
        city = usr.get('location').get('city') if usr.get('location') else None
        restored_city = predict_unknown_attribute(friends.get('items'), 'location')
        image_url = usr.get('pic190x190')
        ok_user = cls(
            uid=id_ok,
            friends=friends,
            id_ok=id_ok,
            first_name=usr.get('first_name'),
            last_name=usr.get('last_name'),
            age=age,
            restored_age=restored_age,
            city=city,
            restored_city=restored_city,
            image_url=image_url,
        )
        return ok_user

    def _update_friends(self, token):
        app_key = get_ok_app_key()
        app_secret = get_ok_app_secret_key()
        try:
            self.friends = ok.get_user_friends(app_key, app_secret, token, self.id_ok)
        except ApiRequestError:
            self.friends = {'items': [], 'count': 0}
        self.save()
