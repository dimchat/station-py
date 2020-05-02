<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:import href="layout.xsl"/>

    <xsl:template match="/">
        <xsl:call-template name="layout"/>
    </xsl:template>
    
    <xsl:template name="title">
        <link rel="stylesheet" href="/static/css/home.css"/>
        <title><xsl:value-of select="//head/title"/></title>
    </xsl:template>

    <xsl:template name="panel">
        <div class="outlines">
            <div><h2>Users</h2></div>
            <xsl:apply-templates select="//outline"/>
        </div>
    </xsl:template>

    <xsl:template name="main">
        <xsl:call-template name="form"/>
        <div id="headlines">
            <div><h2>Messages</h2></div>
            <div id="messages"/>
            <div id="message_template">
                <div class="msg">
                    <div>
                        <span class="timestamp">${time}</span>
                    </div>
                    <div>
                        <a href="${{link}}">${title}</a>
                    </div>
                    <div class="desc">${data}</div>
                </div>
            </div>
        </div>
        <script src="anyone.js"/>
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

    <xsl:template name="form">
        <div id="post_box" class="input_box">
            <div id="post_box_mask" class="input_box_mask">
                <div>
                    <button onClick="javascript:dwitter.showRegisterWindow();">Create Account</button>
                </div>
            </div>
            <div id="post_box_form" class="input_box_form">
                <textarea id="post_text" class="input_text"/>
                <span id="input_limit" class="input_limit">bytes left</span>
                <button id="post_button" class="input_submit">Submit</button>
            </div>
        </div>
    </xsl:template>

</xsl:stylesheet>