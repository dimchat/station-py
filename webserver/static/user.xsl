<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:import href="layout.xsl"/>

    <xsl:template match="/">
        <xsl:call-template name="layout"/>
    </xsl:template>

    <xsl:template name="title">
        <link rel="stylesheet" href="/static/css/home.css"/>
        <title><xsl:value-of select="//channel/title"/></title>
    </xsl:template>

    <xsl:template name="panel">
        <h1><xsl:value-of select="//channel/title"/></h1>
        <div class="desc">
            <span><xsl:value-of select="//channel/description"/></span>
        </div>
    </xsl:template>

    <xsl:template name="main">
        <div class="messages">
            <div><h2>Messages</h2></div>
            <xsl:apply-templates select="//item"/>
        </div>
    </xsl:template>

    <xsl:template match="item">
        <div class="msg">
            <div>
                <span class="timestamp"><xsl:value-of select="pubDate"/></span>
            </div>
            <div>
                <a>
                    <xsl:attribute name="href">
                        <xsl:value-of select="link"/>
                    </xsl:attribute>
                    <xsl:value-of select="title"/>
                </a>
            </div>
            <div class="desc">
                <xsl:value-of select="description"/>
            </div>
        </div>
    </xsl:template>

</xsl:stylesheet>
