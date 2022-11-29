<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:import href="layout.xsl"/>
    <xsl:import href="templates.xsl"/>

    <xsl:template match="/">
        <xsl:call-template name="layout"/>
    </xsl:template>
    
    <xsl:template name="title">
        <link rel="stylesheet" href="/static/css/home.css"/>
        <script src="/static/js/submit.js"/>
        <title><xsl:value-of select="//head/title"/> - Dwitter</title>
    </xsl:template>

    <xsl:template name="panel">
        <div class="outlines">
            <div><h2>Users</h2></div>
            <xsl:apply-templates select="//outline"/>
        </div>
    </xsl:template>

    <xsl:template name="main">
        <div id="headlines">
            <div><h2>Messages</h2></div>
            <div id="messages" class="messages"/>
            <xsl:call-template name="message_template"/>
        </div>
        <script>
            !function (ns) {
                ns.addOnLoad(function () {
                    ns.js.request(ns.baseURL + 'channel/anyone@anywhere.js');
                });
            }(dwitter);
        </script>
    </xsl:template>

    <xsl:template match="outline">
        <div class="user">
            <div class="name">
                <a>
                    <xsl:attribute name="href">
                        <xsl:value-of select="@xmlUrl"/>
                    </xsl:attribute>
                    <xsl:value-of select="@title"/>
                </a>
            </div>
        </div>
    </xsl:template>

</xsl:stylesheet>
