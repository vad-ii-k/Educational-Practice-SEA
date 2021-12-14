"""Social graph of friends"""
from itertools import islice

from pyvis.network import Network


class SocialGraph:

    def __init__(self, user, mutual, friend_uids):
        self.user = user
        self.mutual = mutual
        self.friend_uids = friend_uids
        self.graph = self._get_graph()
        self.close_friends = self._get_close_friends()

    def _get_graph(self):
        graph = Network(
            heading='Social graph of friends')
        graph.show_buttons()
        friends = self.user.friends
        graph.add_node(
            int(self.user.uid),
            shape="circularImage",
            label=self.user.first_name,
            title=self.user.last_name,
            color='#FF7092',
            size=25,
            mas=20,
            image=self.user.image_url
        )
        for value in friends.get('items'):
            size = 20
            color = "#007BFF"
            graph.add_node(
                int(value.get('id') or value.get('uid')),
                shape="circularImage",
                label=value.get('last_name'),
                title=value.get('last_name'),
                color=color,
                size=size,
                mas=size,
                image=value.get('photo_200') or value.get('pic190x190')
            )
        for friend, mutuals in self.mutual.items():
            if mutuals:
                for edge in mutuals:
                    graph.add_edge(int(friend), int(edge), physics=True)
        for friend in self.friend_uids:
            graph.add_edge(int(self.user.uid), int(friend), physics=True)

        graph.barnes_hut(
            gravity=-80000,
            central_gravity=2,
            spring_length=250,
            spring_strength=0.01,
            damping=0.09,
            overlap=0.1
        )
        return graph

    def _get_close_friends(self):
        close_friends_uids = list(
            uid for uid, _ in islice(
                sorted(self.mutual.items(),
                       key=lambda friend: len(friend[1]) if friend[1] else 0,
                       reverse=True)
                , 3
            )
        )
        close_friends = list(
            filter(
                lambda u:
                u.get('id') in close_friends_uids if u.get('id')
                else int(u.get('uid')) in close_friends_uids,
                self.user.friends.get('items')
            )
        )
        return close_friends
