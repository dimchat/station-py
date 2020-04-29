<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:import href="common.xsl"/>
    <xsl:import href="header.xsl"/>
    <xsl:import href="footer.xsl"/>

    <xsl:template match="/">
        <html lang="en">
            <head>
                <xsl:copy-of select="$common"/>
                <title><xsl:value-of select="rss/channel/title"/></title>
            </head>
            <body>
                <xsl:copy-of select="$header"/>
                <div class="wrapper">

                    <h1><xsl:value-of select="rss/channel/title"/></h1>
                    <div class="desc">
                        <xsl:value-of select="rss/channel/description"/>
                    </div>

                    <h2>Messages</h2>
                    <div class="messages">
                        <xsl:apply-templates select="//item"/>
                    </div>

                </div>
                <xsl:copy-of select="$footer"/>
            </body>
        </html>
    </xsl:template>

    <xsl:template match="item">
        <div class="msg">
            <a>
                <xsl:attribute name="href">
                    <xsl:value-of select="link"/>
                </xsl:attribute>
                <xsl:value-of select="title"/>
            </a>
        </div>
    </xsl:template>

</xsl:stylesheet>
