
dwitter.js = dim.js;

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
            return /^\/channel\/[^\/]+\.js$/.test(path);
        },
        function (json) {
            var channel = json['channel'];
            if (!channel) {
                console.error('user messages error: ' + JSON.stringify(json));
                return;
            }
            var items = channel['item'];
            if (!items || items.length === 0) {
                console.log('message empty');
                return;
            }
            for (var i = 0; i < items.length; ++i) {
                var msg = items[i]['msg'];
                suspend(msg);
            }
            console.log('received messages: ', items.length);
            var nc = DIMP.stargate.NotificationCenter.getInstance();
            nc.postNotification('MessageReceived', this,
                {'channel': channel});
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

    var msg_filename = function (signature) {
        var start = 0;
        var length = signature.length;
        while (length > 16) {
            start += 4;
            length -= 4;
        }
        var filename;
        if (start > 0) {
            filename = signature.substring(start);
        } else {
            filename = signature;
        }
        return filename
            .replace('+', '-')
            .replace('/', '_')
            .replace('=', '');
    };

    var msg_url = function (msg) {
        var signature = msg['signature'];
        if (!signature) {
            return null;
        }
        return '/message/' + msg_filename(signature);
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
            return /^\/channel\/[^\/]+\.js$/.test(path);
        },
        function () {
            var messages = ns.suspendingMessages();
            ns.showMessages(messages);
        }
    );

    // callback for showing messages after receive meta
    ns.js.addObserver(
        function (request) {
            var path = request['path'];
            return /^\/meta\/[^.]+\.js$/.test(path);
        },
        function (json, request) {
            var path = request['path'];
            var pos = path.indexOf('.js');
            var identifier = path.substring('/meta/'.length, pos);
            if (!identifier) {
                console.error('id error: ', request);
                return;
            }
            var messages = ns.suspendingMessages(identifier);
            ns.showMessages(messages);
        }
    );

}(dwitter);

!function (ns, im) {
    'use strict';

    var show_content = function (div, json) {
        var content = null;
        if (json) {
            var dict = DIMP.format.JSON.decode(json);
            content = DIMP.Content.getInstance(dict);
        }
        if (content) {
            var builder = DIMP.cpu.MessageBuilder;
            div.innerText = builder.getContentText(content);
        } else {
            div.innerText = 'Signature error!';
            div.style.color = 'red';
        }
    };

    var verify = function (div) {
        if (typeof DIMP !== 'object') {
            console.error('DIM not load yet');
            return;
        }
        // get message fields
        var divSender = div.getElementsByClassName('sender');
        var divData = div.getElementsByClassName('data');
        var divSignature = div.getElementsByClassName('signature');
        var divContent = div.getElementsByClassName('content');
        if (divSender.length !== 1 ||
            divData.length !== 1 ||
            divSignature.length !== 1 ||
            divContent.length !== 1) {
            // error
            return;
        }
        // get field values
        var identifier = divSender[0].innerText;
        var json = divData[0].innerText;
        var base64 = divSignature[0].innerText;
        if (identifier.charAt(0) === '$') {
            // template
            return;
        }

        var facebook = DIMP.Facebook.getInstance();
        identifier = facebook.getIdentifier(identifier);
        if (!identifier) {
            console.error('sender error: ', divSender);
            return;
        }
        var meta = im.getMeta(identifier);
        if (!meta) {
            // waiting for meta
            return;
        }
        var data = DIMP.format.UTF8.encode(json);
        var signature = DIMP.format.Base64.decode(base64);
        if (meta.key.verify(data, signature)) {
            // show content
            show_content(divContent[0], json);
        } else {
            // error
            console.error('message signature not match: ', json, base64);
            show_content(divContent[0], null);
        }
        // remove data & signature fields
        tarsier.ui.$(divData[0].parentNode).remove();
        tarsier.ui.$(divSignature[0].parentNode).remove();
    };

    var verify_all = function () {
        var messages = document.getElementsByClassName('message');
        for (var i = 0; i < messages.length; ++i) {
            verify(messages[i]);
        }
    };

    ns.addOnLoad(verify_all);

    // call it after received messages in channel
    ns.js.addObserver(
        function (request) {
            var path = request['path'];
            return /^\/channel\/[^\/]+\.js$/.test(path);
        },
        verify_all
    );

    // call it after received meta
    ns.js.addObserver(
        function (request) {
            var path = request['path'];
            return /^\/meta\/[^.]+\.js$/.test(path);
        },
        verify_all
    );

}(dwitter, dim);
