
!function () {
    'use strict';

    var headlines = document.getElementById('headlines');

    var template = document.getElementById('headline_template');
    template = template.innerHTML;

    var create_element = function (tmpl, dict) {
        var html = tmpl;
        var tag, key, value;
        for (key in dict) {
            if (!dict.hasOwnProperty(key)) {
                continue;
            }
            value = dict[key];
            tag = '{{' + key + '}}';
            html = html.replace(tag, value);
            tag = '%7B' + key + '%7D';
            html = html.replace(tag, value);
        }
        return html;
    };

    // callback for showing messages
    dwitter.js.addObserver(
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
            var messages = channel['item'];
            if (!messages) {
                return;
            }
            for (var i = 0; i < messages.length; ++i) {
                var msg = messages[i];
                var html = create_element(template, msg);
                headlines.innerHTML += html;
            }
        }
    );

}();
