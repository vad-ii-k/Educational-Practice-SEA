"""Social graph of friends"""
from itertools import islice

from pyvis.network import Network


class SocialGraph:

    def __init__(self, user, friend_uids, mutual, gifts, likes, comments):
        self.user = user
        self.mutual = mutual
        self.friend_uids = friend_uids
        self.graph = self._get_graph()
        self.gifts = self._get_edges_from_metrics(gifts)
        self.likes = self._get_edges_from_metrics(likes)
        self.comments = self._get_edges_from_metrics(comments)
        self.close_friends = self._get_close_friends()

    def _get_graph(self):
        graph = Network(
            heading='Social graph of friends')

        friends = self.user.friends
        graph.add_node(
            int(self.user.uid),
            shape="circularImage",
            label=self.user.first_name,
            title=self.user.first_name + ' ' + self.user.last_name,
            color='#FF7092',
            size=50,
            mas=5,
            image=self.user.image_url
        )

        for value in friends.get('items'):
            graph.add_node(
                int(value.get('id') or value.get('uid')),
                shape="circularImage",
                label=value.get('last_name'),
                title=value.get('first_name') + ' ' + value.get('last_name'),
                color='#000000',
                size=35,
                mas=4,
                image=value.get('photo_200') or value.get('pic190x190')
            )
            
        for friend1, mutuals in self.mutual.items():
            if mutuals:
                for friend2 in mutuals:
                    graph.add_edge(
                        int(friend1),
                        int(friend2),
                        value=len(list(set(self.mutual[friend1]) & set(self.mutual[friend2]))) if friend2 in self.mutual else 0,
                        title='from: ' + graph.get_node(int(friend1))['title'] + '\nto:   ' + graph.get_node(int(friend2))['title']
                    )
        for friend in self.friend_uids:
            graph.add_edge(
                int(self.user.uid),
                int(friend),
                color='#FF7092',
                value=len(self.mutual[friend]) if friend in self.mutual else 0,
                title='from: ' + graph.get_node(int(self.user.uid))['title'] + '\nto:   ' + graph.get_node(int(friend))['title']
            )

        graph.set_options('''
                var options = {
                    "autoResize" : true,
                    "configure": {
                        "enabled": false
                    },
                    "edges": {
                        "color": {
                            "color": "#007BFF",
                            "highlight": "#000000",
                            "opacity": 0.7
                        },
                        "smooth": {
                            "enabled": true,
                            "type": "continuous"
                        },
                        "shadow": {
                            "enabled": true,
                            "size": 5
                        }
                    },
                    "nodes": {
                        "font": {
                            "size": 20,
                            "strokeWidth": 3
                        },
                        "borderWidthSelected": 15,
                        "labelHighlightBold": true,
                        "highlight": {
                            "border": "#000000"
                        },
                        "shapeProperties": {
                            "interpolation": false
                        }
                    },
                    "interaction": {
                        "freezeForStabilization": true,
                        "dragNodes": true,
                        "hideEdgesOnDrag": false,
                        "hideNodesOnDrag": false
                    },
                    "physics": {
                        "barnesHut": {
                            "avoidOverlap": 0.1,
                            "centralGravity": 1.5,
                            "damping": 0.05,
                            "gravitationalConstant": -100000,
                            "springConstant": 0.01,
                            "springLength": 600
                        },
                        "enabled": true,
                        "stabilization": {
                            "enabled": false,
                            "fit": true,
                            "iterations": 1000,
                            "onlyDynamicEdges": false,
                            "updateInterval": 100
                        }
                    },
                    "layout": {
                        "improvedLayout": true,
                        "randomSeed": 10
                    }
                }
            ''')

        return graph


    def _get_edges_from_metrics(self, metric):
        edges = []
        for friend1 in metric:
            for friend2 in metric[friend1]:
                if metric[friend1][friend2] > 0:
                    if self.user.uid == friend1 or self.user.uid == friend2:
                        edges.append({
                            'from': friend2,
                            'to': friend1,
                            'arrows': 'middle',
                            'value': metric[friend1][friend2],
                            'color': '#FF7092',
                            'title': 'from: ' + self.graph.get_node(int(friend2))['title'] + '\nto:   ' + self.graph.get_node(int(friend1))['title']
                            })
                    else:
                        edges.append({
                            'from': friend2,
                            'to': friend1,
                            'arrows': 'to',
                            'value': metric[friend1][friend2],
                            'title': 'from: ' + self.graph.get_node(int(friend2))['title'] + '\nto:   ' + self.graph.get_node(int(friend1))['title']
                            })
        return edges


    def _get_close_friends(self):
        close_friends_uids = list(
            uid for uid, _ in islice(
                sorted(self.mutual.items(), key=lambda friend: len(friend[1]) if friend[1] else 0, reverse=True), 3)
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