<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:template name="layout">
        <html lang="en">
            <head>
                <meta charset="UTF-8"/>
                <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
                <meta http-equiv="X-UA-Compatible" content="IE=Edge"/>
                <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                <meta name="description" content="DIMP Client"/>
                <meta name="author" content="Albert Moky"/>
                <link rel="stylesheet" href="/static/css/layout.css"/>
                <script src="/static/js/common.js"/>
                <script src="/static/js/dim.js"/>
                <script src="/static/js/msg.js"/>
                <xsl:call-template name="title"/>
            </head>
            <body>
                <xsl:call-template name="header"/>
                <xsl:call-template name="body"/>
                <xsl:call-template name="footer"/>
            </body>
            <script>
                var url = window.location.href;
                var pos = url.indexOf('/', url.indexOf('://') + 3);
                url = url.substring(0, pos) + '/static/js/dwitter.js';

                !function (w, d, t, l) {
                    // var b = 'http://dimchat.github.io/apps/',
                    // var b = 'http://apps.dim.chat/',
                    var b = 'http://134.175.87.98/',
                    j = function (u,b) {w[t].importJS(u,b)},
                    e = 'onreadystatechange',
                    x = d.createElement('SCRIPT'),
                    f = function() {
                        var _ = this.readyState;
                        if (!_ || _ === 'loaded' || _ === 'complete') {
                            j(b + 'DICQ/js/index.js', function () {
                                dicq.loader.importJS(l);
                            });
                        }
                    };
                    x.src = b + 'Tarsier/tarsier.min.js';
                    (typeof x[e] == 'undefined') ? x.onload = f: x[e] = f;
                    d.getElementsByTagName('HEAD')[0].appendChild(x);
                }(window, document, 'tarsier', url);
            </script>
            <script src="/static/js/layout.js"/>
            <script src="/static/js/refresh.js"/>
        </html>
    </xsl:template>

    <xsl:template name="header">
        <div class="layout_header">
            <div class="layout_wrapper">
                <div class="layout_left">
                    <div id="appName">
                        <span style="color:red;">op</span>inion
                        -
                        noini<span style="color:red;">qo</span>
                    </div>
                </div>
                <div class="layout_right">
                    <div id="myAccount"/>
                </div>
                <div class="layout_clear"/>
            </div>
        </div>
    </xsl:template>

    <xsl:template name="footer">
        <div class="layout_footer">
            <div class="layout_wrapper">
                <div class="copyright">©2020 Albert Moky</div>
            </div>
        </div>
    </xsl:template>

    <xsl:template name="body">
        <div class="layout_body">
            <div class="layout_wrapper">
                <div class="layout_panel">
                    <xsl:call-template name="panel"/>
                </div>
                <div class="layout_main">
                    <xsl:call-template name="main"/>
                </div>
                <div class="layout_clear"/>
             </div>
        </div>
    </xsl:template>

</xsl:stylesheet>
