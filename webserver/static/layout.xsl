<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:template name="layout">
        <html lang="en">
            <head>
                <meta charset="UTF-8" />
                <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
                <meta http-equiv="X-UA-Compatible" content="IE=Edge" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <meta name="description" content="DIMP Client" />
                <meta name="author" content="Albert Moky" />
                <link rel="stylesheet" href="/static/css/layout.css" />
                <xsl:call-template name="title"/>
            </head>
            <body>
                <xsl:call-template name="header"/>
                <xsl:call-template name="body"/>
                <xsl:call-template name="footer"/>
            </body>
        </html>
    </xsl:template>

    <xsl:template name="header">
        <div class="layout_header">
            <div class="layout_wrapper">
                <div>Dwitter (v0.1.0) powered by DIMP</div>
            </div>
        </div>
    </xsl:template>

    <xsl:template name="footer">
        <div class="layout_footer">
            <div class="layout_wrapper">
                <div>Albert Moky (c) 2020</div>
            </div>
        </div>
    </xsl:template>

    <xsl:template name="body">
        <div class="layout_body">
            <div class="layout_wrapper">
                <div class="layout_main">
                    <xsl:call-template name="main"/>
                </div>
                <div class="layout_panel">
                    <xsl:call-template name="panel"/>
                </div>
                <div class="layout_clear"/>
             </div>
        </div>
    </xsl:template>

</xsl:stylesheet>