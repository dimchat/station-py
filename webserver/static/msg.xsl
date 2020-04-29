<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:import href="common.xsl"/>
    <xsl:import href="header.xsl"/>
    <xsl:import href="footer.xsl"/>

    <xsl:template match="/">
        <html lang="en">
            <head>
                <xsl:copy-of select="$common"/>
                <title><xsl:value-of select="message/content/title"/></title>
            </head>
            <body>
                <xsl:copy-of select="$header"/>
                <div class="wrapper">

                    <h1><xsl:value-of select="message/content/title"/></h1>

                    <div class="sender">
                        <span><b>Sender</b>: </span>
                        <span><xsl:value-of select="message/envelope/sender"/></span>
                    </div>
                    <div class="time">
                        <span><b>Time</b>: </span>
                        <span id="msg_time"><xsl:value-of select="message/envelope/time"/></span>
                        <script>
                            (function () {
                                var span = document.getElementById('msg_time');
                                var value = parseInt(span.innerText) * 1000;
                                var time = new Date(value);
                                span.innerText = time;
                            })();
                        </script>
                    </div>

                    <div class="content">
                        <div><b>Content</b>: </div>
                        <div class="text">
                            <xsl:value-of select="message/content/text"/>
                        </div>
                    </div>

                    <h3>Comments</h3>
                    <div id="comments" class="comments">
                        <!-- Loading -->
                    </div>

                </div>
                <xsl:copy-of select="$footer"/>
            </body>
        </html>
    </xsl:template>

</xsl:stylesheet>
