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
        <div class="sender">
            <span><b>Sender</b>: </span>
            <span><xsl:value-of select="//envelope/sender"/></span>
        </div>
    </xsl:template>

    <xsl:template name="main">
        <h1><xsl:value-of select="//content/title"/></h1>

        <div class="time">
            <span><b>Time</b>: </span>
            <span class="timestamp"><xsl:value-of select="//envelope/time"/></span>
        </div>

        <div class="content">
            <div><b>Content</b>: </div>
            <div class="text">
                <xsl:value-of select="//content/text"/>
            </div>
        </div>

        <xsl:call-template name="comments"/>
    </xsl:template>

    <xsl:template name="comments">
        <div id="comments" class="comments">
            <span style="color: lightgray; ">Loading comments ...</span>
            <!-- Loading -->
        </div>
    </xsl:template>

</xsl:stylesheet>
