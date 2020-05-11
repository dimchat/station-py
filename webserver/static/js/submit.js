
!function (ns) {
    'use strict';

    var len = function (string) {
        if (typeof DIMP === 'object') {
            var array = DIMP.format.UTF8.encode(string);
            return array.length;
        } else {
            return string.length;
        }
    };

    var onchange = function () {
        var limit = this.limit;
        var value = this.value;
        var left = limit - len(value);
        if (left > 1) {
            this.tips.innerText = left + ' bytes left';
        } else if (left === 1) {
            this.tips.innerText = '1 byte left';
        } else if (left === 0) {
            this.tips.innerText = 'space full';
        } else if (left === -1) {
            this.tips.innerText = '1 byte overflows';
        } else {
            this.tips.innerText = (-left) + ' bytes overflow';
        }
    };

    var limit = function (input, length, span) {
        input.onkeyup = onchange;
        input.limit = length;
        input.tips = span;
    };

    var process = function () {
        var textarea, span;
        textarea = document.getElementById('post_text');
        span = document.getElementById('input_limit');
        if (textarea && span) {
            limit(textarea, 420, span);
        }
        textarea = document.getElementById('reply_text');
        // span = document.getElementById('input_limit');
        if (textarea && span) {
            limit(textarea, 420, span);
        }
    };

    ns.addOnLoad(process);

}(dwitter);
