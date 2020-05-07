<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:import href="layout.xsl"/>
    <xsl:import href="templates.xsl"/>

    <xsl:template match="/">
        <xsl:call-template name="layout"/>
    </xsl:template>

    <xsl:template name="title">
        <link rel="stylesheet" href="/static/css/home.css"/>
        <title><xsl:value-of select="//title"/> - Dwitter</title>
    </xsl:template>

    <xsl:template name="panel">
        <h1><xsl:value-of select="//title"/></h1>
        <div class="desc">
            <span class="profile"><xsl:value-of select="//description"/></span>
        </div>
    </xsl:template>

    <xsl:template name="main">
        <div class="messages">
            <div><h2>Messages</h2></div>
            <div id="messages">
                <xsl:apply-templates select="//item"/>
            </div>
            <xsl:call-template name="message_template"/>
        </div>
    </xsl:template>

</xsl:stylesheet>
