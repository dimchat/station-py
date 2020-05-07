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
        <title><xsl:value-of select="//content/text"/> - Dwitter</title>
    </xsl:template>

    <xsl:template name="panel">
        <div class="user">
            <img class="avatar" src="http://apps.dim.chat/DICQ/images/icon-120.png">
                <xsl:attribute name="did">
                    <xsl:value-of select="//sender"/>
                </xsl:attribute>
            </img>
            <div><xsl:apply-templates select="//sender"/></div>
        </div>
    </xsl:template>

    <xsl:template name="main">
        <div class="message">
            <div class="field">
                <span><b>Sender</b>: </span>
                <span class="sender"><xsl:apply-templates select="//sender"/></span>
            </div>

            <div class="field">
                <span><b>Time</b>: </span>
                <span class="timestamp"><xsl:value-of select="//time"/></span>
            </div>

            <div class="field">
                <div><b>Content</b>: </div>
                <div class="content">
                    <div class="text">
                        <xsl:value-of select="//content/text"/>
                    </div>
                </div>
            </div>

            <div class="field">
                <div><b>Data</b>: </div>
                <div class="data"><xsl:value-of select="//data"/></div>
            </div>

            <div class="field">
                <div><b>Signature</b>: </div>
                <div class="signature"><xsl:value-of select="//signature"/></div>
            </div>
        </div>

        <div class="comments">
            <xsl:call-template name="comments"/>
        </div>
    </xsl:template>

    <xsl:template name="comments">
        <xsl:call-template name="form"/>

        <div id="comments">
            <span style="color: lightgray; ">Loading comments ...</span>
            <!-- Loading -->
        </div>
    </xsl:template>

    <xsl:template name="form">
        <div id="reply_box" class="input_box">
            <div id="reply_box_mask" class="input_box_mask">
                <div>
                    <button onClick="javascript:dwitter.showRegisterWindow();">Create Account</button>
                </div>
            </div>
            <div id="reply_box_form" class="input_box_form">
                <textarea id="reply_text" class="input_text"/>
                <span id="input_limit" class="input_limit"/>
                <button id="reply_button" class="input_submit">Reply</button>
            </div>
        </div>
    </xsl:template>

</xsl:stylesheet>
