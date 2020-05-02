
!function (ns) {
    'use strict';

    //
    //  Suspend Messages
    //

    var s_waiting_list = [];

    var suspend = function (msg) {
        if (!msg) {
            alert('message empty');
            return;
        }
        // TODO: check duplicated message
        s_waiting_list.push(msg);
    };

    var get_messages = function (sender, copy) {
        var messages;
        if (sender) {
            messages = [];
            var msg;
            for (var i = s_waiting_list.length - 1; i >= 0; --i) {
                msg = s_waiting_list[i];
                if (sender === msg['sender']) {
                    messages.push(msg);
                    if (!copy) {
                        s_waiting_list.splice(i, 1);
                    }
                }
            }
            messages = messages.reverse();
        } else {
            messages = s_waiting_list;
            if (!copy) {
                s_waiting_list = [];
            }
        }
        return messages;
    };

    // callback for receiving messages
    ns.js.addObserver(
        function (request) {
            var path = request['path'];
            return /^\/dwitter\/[^\/]+\.js$/.test(path);
        },
        function (json) {
            var channel = json['channel'];
            if (!channel) {
                console.error('user messages error: ' + JSON.stringify(json));
                return;
            }
            var items = channel['item'];
            if (!items) {
                return;
            }
            for (var i = 0; i < items.length; ++i) {
                var msg = items[i]['msg'];
                suspend(msg);
            }
        }
    );

    ns.suspendMessage = suspend;
    ns.suspendingMessages = get_messages;

}(dwitter);

!function (ns) {
    'use strict';

    //
    //  Show Message
    //

    var show = function (messages, container, template) {
        if (!messages || messages.length === 0) {
            return;
        }
        if (!container) {
            container = document.getElementById('messages');
        }
        if (!template) {
            template = document.getElementById('message_template');
            template = template.innerHTML;
        }
        for (var i = 0; i < messages.length; ++i) {
            var msg = messages[i];
            var html = create(template, msg);
            if (html) {
                container.innerHTML += html;
            }
        }
        ns.refreshTimestamp();
    };

    var create = function (template, msg) {
        msg = verify(msg);
        if (!msg) {
            return null;
        }
        var title = msg['title'];
        if (!title) {
            var content = DIMP.format.JSON.decode(msg['data']);
            msg['title'] = content['text'];
        }
        var link = msg['link'];
        if (!link) {
            link = msg_url(msg);
            if (link) {
                msg['link'] = link;
            }
        }
        return ns.template(template, msg);
    };

    var msg_url = function (msg) {
        var time = new Date(msg['time'] * 1000);
        var year = time.getFullYear();
        var month = time.getMonth() + 1;
        var day = time.getDate();
        var signature = msg['signature'];
        signature = signature.substring(signature.length - 8);
        return '/dwitter/' + year + '/' + month + '/' + day + '/' + signature
    };

    var verify = function (msg) {
        if (typeof DIMP !== 'object') {
            console.log('DIM not loaded yet, add message to waiting list');
            ns.suspendMessage(msg);
            return null;
        }
        var facebook = DIMP.Facebook.getInstance();
        var sender = facebook.getIdentifier(msg['sender']);
        if (!sender) {
            console.error('message error: ', msg);
            return null;
        }
        var meta = ns.getMeta(sender);
        if (!meta) {
            console.log('meta not found, waiting meta: ' + sender);
            ns.suspendMessage(msg);
            return null;
        }
        var rMsg = DIMP.ReliableMessage.getInstance(msg);
        rMsg.delegate = DIMP.Messenger.getInstance();
        var data = rMsg.getData();
        var signature = rMsg.getSignature();
        if (!meta.key.verify(data, signature)) {
            console.error('message error: ', msg, meta);
            return null;
        }
        return msg;
    };

    ns.showMessages = show;

}(dwitter);

!function (ns) {
    'use strict';

    ns.addOnLoad(function () {
        var messages = ns.suspendingMessages();
        ns.showMessages(messages);
    });

    // callback for showing messages
    ns.js.addObserver(
        function (request) {
            var path = request['path'];
            return /^\/dwitter\/[^\/]+\.js$/.test(path);
        },
        function (json) {
            var messages = ns.suspendingMessages();
            ns.showMessages(messages);
        }
    );

    // callback for showing messages after receive meta
    ns.js.addObserver(
        function (request) {
            var path = request['path'];
            return /^\/dwitter\/[^\/]+\/meta\.js$/.test(path);
        },
        function (json, request) {
            var path = request['path'];
            var pos = path.indexOf('/meta.js');
            var identifier = path.substring('/dwitter/'.length, pos);
            if (!identifier) {
                console.error('id error: ', request);
                return;
            }
            var messages = ns.suspendingMessages(identifier);
            ns.showMessages(messages);
        }
    );

}(dwitter);
