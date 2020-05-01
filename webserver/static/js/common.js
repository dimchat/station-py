
if (typeof dwitter !== 'object') {
    dwitter = {}
}

!function () {
    'use strict';

    var observers = [];

    /**
     *  Callback for JS request
     */
    dwitter.js = {
        respond: function (json, request) {
            var ob;
            for (var i = 0; i < observers.length; ++i) {
                ob = observers[i];
                if (ob.evaluate(request)) {
                    ob.callback(json);
                }
            }
        },
        addObserver: function (evaluate, callback) {
            for (var i = observers.length - 1; i >= 0; --i) {
                var item = observers[i];
                if (item['evaluate'] === evaluate &&
                    item['callback'] === callback) {
                    alert('duplicate observer');
                    return;
                }
            }
            observers.push({
                'evaluate': evaluate,
                'callback': callback
            });
        },
        removeObserver: function (evaluate, callback) {
            for (var i = observers.length; i >= 0; --i) {
                var item = observers[i];
                if (item['evaluate'] === evaluate &&
                    item['callback'] === callback) {
                    observers.splice(i, 1);
                }
            }
        }
    };

}();

!function () {
    'use strict';

    dwitter.showRegisterWindow = function () {
        if (!dwitter.im) {
            alert('loading DIM ...');
            return;
        }
        dwitter.im.RegisterWindow.show();
    };

}();
