<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:template name="message_template">
        <div id="message_template">
            <div class="message">
                <div class="sender">
                    <a did="${{sender}}" href="../channel/${{sender}}">
                        <span class="nickname" did="${{sender}}">${sender}</span>
                    </a>
                </div>
                <div class="field">
                    <span class="content"/>
                </div>
                <div class="field">
                    <div class="timestamp">${time}</div>
                    <a class="link" href="${{link}}">
                        <span>comments</span>
                    </a>
                </div>

                <div class="field">
                    <div><b>Data</b>: </div>
                    <div class="data">${data}</div>
                </div>

                <div class="field">
                    <div><b>Signature</b>: </div>
                    <div class="signature">${signature}</div>
                </div>
            </div>
        </div>
    </xsl:template>

    <xsl:template name="sender_link" match="sender">
        <a>
            <xsl:attribute name="did">
                <xsl:value-of select="text()"/>
            </xsl:attribute>
            <xsl:attribute name="href">
                ../channel/<xsl:value-of select="text()"/>
            </xsl:attribute>
            <span class="nickname">
                <xsl:attribute name="did">
                    <xsl:value-of select="text()"/>
                </xsl:attribute>
                <xsl:value-of select="text()"/>
            </span>
        </a>
    </xsl:template>

    <xsl:template match="item">
        <div class="message">
            <div class="sender">
                <xsl:apply-templates select="msg/sender"/>
            </div>
            <div class="field">
                <span class="content"/>
            </div>
            <div class="field">
                <div class="timestamp"><xsl:value-of select="msg/time"/></div>
                <a class="link">
                    <xsl:attribute name="href">
                        <xsl:value-of select="link"/>
                    </xsl:attribute>
                    <span>comments</span>
                </a>
            </div>

            <div class="field">
                <div><b>Data</b>: </div>
                <div class="data"><xsl:value-of select="msg/data"/></div>
            </div>

            <div class="field">
                <div><b>Signature</b>: </div>
                <div class="signature"><xsl:value-of select="msg/signature"/></div>
            </div>
        </div>
    </xsl:template>

    <xsl:template name="post_box">
        <div id="post_box" class="input_box">
            <div id="post_box_mask" class="input_box_mask">
                <div>
                    <button onClick="javascript:dwitter.showRegisterWindow();">Create Account</button>
                </div>
            </div>
            <div id="post_box_form" class="input_box_form">
                <textarea id="post_text" class="input_text"/>
                <span id="input_limit" class="input_limit"/>
                <button id="post_button" class="input_submit">Submit</button>
            </div>
        </div>
    </xsl:template>

    <xsl:template name="reply_box">
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
