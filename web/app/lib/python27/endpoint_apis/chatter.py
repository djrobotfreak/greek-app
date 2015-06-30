from ndbdatastore import Chatter, ChatterComment, User
from apiconfig import *
from protorpc import remote
import datetime
import logging

chatter_api = endpoints.api(name='chatter', version='v1',
                            allowed_client_ids=[WEB_CLIENT_ID, ANDROID_CLIENT_ID, IOS_CLIENT_ID],
                            audiences=[ANDROID_AUDIENCE])

@chatter_api.api_class(resource_name='chatter')
class ChatterApi(remote.Service):
    @endpoints.method(IncomingMessage, OutgoingMessage, path='get', http_method='POST', name='chatter.get')
    def get_chatter(self, request):
        request_user = get_user(request.user_name, request.token)
        if not request_user:
            return OutgoingMessage(error=TOKEN_EXPIRED, data='')
        chatters_future = Chatter.query(Chatter.organization == request_user.organization)\
            .order(-Chatter.timestamp).fetch_async(20)

        important_chatters_future = Chatter.query(Chatter.organization == request_user.organization,
                                           Chatter.important == True).order(-Chatter.timestamp).fetch_async(20)
        chatters = chatters_future.get_result()
        important_chatters = important_chatters_future.get_result()
        chatter_dict = list()
        for chatter in chatters:
            local_chatter_dict = chatter.to_dict()
            local_chatter_dict["key"] = chatter.key
            chatter_dict.append(local_chatter_dict)
        important_chatters_dict = list()

        for chatter in important_chatters:
            local_chatter_dict = chatter.to_dict()
            local_chatter_dict["key"] = chatter.key
            important_chatters_dict.append(local_chatter_dict)

        for chatter in chatter_dict:
            chatter["author_future"] = chatter["author"].get_async()
            if request_user.key in chatter["likes"]:
                chatter["like"] = True

        for chatter in important_chatters_dict:
            chatter["author_future"] = chatter["author"].get_async()
            chatter["likes"] = len(chatter["likes"])
            if request_user.key in chatter["likes"]:
                chatter["like"] = True

        for chatter in chatter_dict:
            chatter["comments_length"] = len(chatter["comments"])
            chatter["likes"] = len(chatter["likes"])
            author = chatter["author_future"].get_result()
            chatter["author"] = {"first_name": author.first_name,
                                 "last_name": author.last_name,
                                 "prof_pic": get_image_url(author.prof_pic),
                                 "key": chatter["author"]}
            del chatter["author_future"]
            del chatter["comments"]

        for chatter in important_chatters_dict:
            chatter["comments_length"] = len(chatter["comments"])
            author = chatter["author_future"].get_result()
            chatter["author"] = {"first_name": author.first_name,
                                 "last_name": author.last_name,
                                 "prof_pic": get_image_url(author.prof_pic),
                                 "key": chatter["author"]}
            del chatter["author_future"]
            del chatter["comments"]
        return OutgoingMessage(error='', data=json_dump({'chatter': chatter_dict,
                                                         'important_chatter': important_chatters_dict}))

    @endpoints.method(IncomingMessage, OutgoingMessage, path='comments/get',
                      http_method='POST', name='chatter.get_comments')
    def get_comments(self, request):
        request_user = get_user(request.user_name, request.token)
        if not request_user:
            return OutgoingMessage(error=TOKEN_EXPIRED, data='')
        data = json.loads(request.data)
        if 'key' not in data:
            return OutgoingMessage(error='Missing arguments in new Chatter.', data='')
        chatter = ndb.Key(urlsafe=data['key']).get()
        chatter_comments = ChatterComment.query(ChatterComment.chatter == chatter.key).order(
                                                -ChatterComment.timestamp).fetch(20)
        comments_dict = list()
        for comment in chatter_comments:
            comments_dict.append(ndb_to_dict(comment))
        author_keys = list()
        for comment in comments_dict:
            comment['like'] = request_user.key in comment['likes']
            comment['likes'] = len(comment['likes'])
            if comment['author'] not in author_keys:
                author_keys.append(comment['author'])
        authors = ndb.get_multi(author_keys)
        for comment in comments_dict:
            for author in authors:
                if author.key == comment['author']:
                    comment['author'] = {"first_name": author.first_name,
                                         "last_name": author.last_name,
                                         "prof_pic": get_image_url(author.prof_pic),
                                         "key": comment['author']}
                    break
        return OutgoingMessage(error='', data=json_dump(comments_dict))

    @endpoints.method(IncomingMessage, OutgoingMessage, path='post',
                      http_method='POST', name='chatter.post')
    def post_chatter(self, request):
        request_user = get_user(request.user_name, request.token)
        if not request_user:
            return OutgoingMessage(error=TOKEN_EXPIRED, data='')
        data = json.loads(request.data)
        if 'content' not in data:
            return OutgoingMessage(error='Missing arguments in new Chatter.', data='')
        chatter = Chatter()
        chatter.content = data["content"]
        chatter.author = request_user.key
        chatter.timestamp = datetime.datetime.now()
        chatter.organization = request_user.organization
        chatter.put()
        return OutgoingMessage(error='', data='OK')

    @endpoints.method(IncomingMessage, OutgoingMessage, path='delete',
                      http_method='POST', name='chatter.delete')
    def delete_chatter(self, request):
        request_user = get_user(request.user_name, request.token)
        if not request_user:
            return OutgoingMessage(error=TOKEN_EXPIRED, data='')
        data = json.loads(request.data)
        if 'key' not in data:
            return OutgoingMessage(error='Missing arguments in deleting Chatter.')
        chatter = ndb.Key(urlsafe=data["key"]).get()
        if not ((chatter.author is request_user.key) or is_admin(request_user)):
            return OutgoingMessage(error='Incorrect Permissions', data='')
        comments_future = ndb.delete_multi_async(chatter.comments)
        chatter_future = chatter.delete_async()
        comments_future.get_result()
        chatter_future.get_result()
        return OutgoingMessage(error='', data='OK')

    @endpoints.method(IncomingMessage, OutgoingMessage, path='edit',
                      http_method='POST', name='chatter.edit')
    def edit_chatter(self, request):
        request_user = get_user(request.user_name, request.token)
        if not request_user:
            return OutgoingMessage(error=TOKEN_EXPIRED, data='')
        data = json.loads(request.data)
        if not all(k in data for k in ('content', 'key')):
            return OutgoingMessage(error='Missing arguments in editing Chatter.')
        chatter = ndb.Key(urlsafe=data["key"]).get()
        chatter.content = data["content"]
        chatter.put()
        return OutgoingMessage(error='', data='OK')

    @endpoints.method(IncomingMessage, OutgoingMessage, path='flag_importance',
                      http_method='POST', name='chatter.importance')
    def change_important_flag(self, request):
        request_user = get_user(request.user_name, request.token)
        if not request_user:
            return OutgoingMessage(error=TOKEN_EXPIRED, data='')
        data = json.loads(request.data)
        if not all(k in data for k in ("importance", "key")):
            return OutgoingMessage(error='Missing arguments in flagging Chatter.')
        chatter = ndb.Key(urlsafe=data["key"]).get()
        # if not type(chatter) is Chatter:
        #     return OutgoingMessage(error='Incorrect type of Key', data='')
        if not is_admin(request_user):
            return OutgoingMessage(error='Incorrect Permissions', data='')
        if data["importance"]:
            chatter.important = True
        else:
            chatter.important = False
        chatter.put()
        return OutgoingMessage(error='', data='OK')

    @endpoints.method(IncomingMessage, OutgoingMessage, path='like',
                      http_method='POST', name='chatter.like')
    def like_chatter(self, request):
        request_user = get_user(request.user_name, request.token)
        if not request_user:
            return OutgoingMessage(error=TOKEN_EXPIRED, data='')
        data = json.loads(request.data)
        logging.error(request.data)
        if not "key" in data:
            return OutgoingMessage(error='Missing arguments in liking Chatter.')
        chatter = ndb.Key(urlsafe=data["key"]).get()
        if request_user.key not in chatter.likes:
            chatter.likes.append(request_user.key)
            chatter.put()
            like = True
        else:
            chatter.likes.remove(request_user.key)
            chatter.put()
            like = False
        return OutgoingMessage(error='', data=json_dump(like))

    @endpoints.method(IncomingMessage, OutgoingMessage, path='comment',
                      http_method='POST', name='chatter.comment')
    def comment_chatter(self, request):
        request_user = get_user(request.user_name, request.token)
        if not request_user:
            return OutgoingMessage(error=TOKEN_EXPIRED, data='')
        data = json.loads(request.data)
        if not all(k in data for k in ("content", "key")):
            return OutgoingMessage(error='Missing arguments in new Chatter.')
        chatter = ndb.Key(urlsafe=data["key"]).get()
        comment = ChatterComment()
        comment.author = request_user.key
        comment.organization = request_user.organization
        comment.timestamp = datetime.datetime.now()
        comment.organization = request_user.organization
        comment.content = data["content"]
        comment.chatter = chatter.key
        chatter.comments.append(comment.put())
        chatter.put()
        return OutgoingMessage(error='', data='OK')

    @endpoints.method(IncomingMessage, OutgoingMessage, path='comment/like',
                      http_method='POST', name='chatter.like_comment')
    def like_comment(self, request):
        request_user = get_user(request.user_name, request.token)
        if not request_user:
            return OutgoingMessage(error=TOKEN_EXPIRED, data='')
        data = json.loads(request.data)
        if not all(k in data for k in ("like", "key")):
            return OutgoingMessage(error='Missing arguments in new Chatter.')
        comment = ndb.Key(urlsafe=data["key"]).get()
        if not type(comment) is ChatterComment:
            return OutgoingMessage(error='Incorrect type of Key', data='')
        if data["like"] is True:
            if request_user.key not in comment.likes:
                comment.likes.append(request_user.key)
        if data["like"] is False:
            if request_user.key in comment.likes:
                comment.likes.remove(request_user.key)
        comment.put()
        return OutgoingMessage(error='', data='OK')

    @endpoints.method(IncomingMessage, OutgoingMessage, path='comment/edit',
                      http_method='POST', name='chatter.edit_comment')
    def edit_comment(self, request):
        request_user = get_user(request.user_name, request.token)
        if not request_user:
            return OutgoingMessage(error=TOKEN_EXPIRED, data='')
        data = json.loads(request.data)
        if not all(k in data for k in ("content", "key")):
            return OutgoingMessage(error='Missing arguments in new Chatter.')
        comment = ndb.Key(urlsafe=data["key"]).get()
        if not type(comment) is ChatterComment:
            return OutgoingMessage(error='Incorrect type of Key', data='')
        comment.content = data["content"]
        comment.put()
        return OutgoingMessage(error='', data='OK')

    @endpoints.method(IncomingMessage, OutgoingMessage, path='comment/delete',
                      http_method='POST', name='chatter.delete_comment')
    def delete_comment(self, request):
        request_user = get_user(request.user_name, request.token)
        if not request_user:
            return OutgoingMessage(error=TOKEN_EXPIRED, data='')
        data = json.loads(request.data)
        if not all(k in data for k in "key"):
            return OutgoingMessage(error='Missing arguments in new Chatter.')
        comment = ndb.Key(urlsafe=data["key"]).get()
        if not type(comment) is ChatterComment:
            return OutgoingMessage(error='Incorrect type of Key', data='')
        if not ((comment.author is request_user.key) or is_admin(request_user)):
            return OutgoingMessage(error='Incorrect Permissions', data='')
        comment.delete()
        return OutgoingMessage(error='', data='OK')