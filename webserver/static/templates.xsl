<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:template name="message_template">
        <div id="message_template">
            <div class="message">
                <div class="timestamp">${time}</div>
                <div class="sender">${sender}</div>
                <div class="field">
                    <a class="link" href="${{link}}">
                        <span class="content"/>
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

    <xsl:template match="item">
        <div class="message">
            <div class="timestamp"><xsl:value-of select="msg/time"/></div>
            <div class="sender"><xsl:value-of select="msg/sender"/></div>
            <div class="field">
                <a class="link">
                    <xsl:attribute name="href">
                        <xsl:value-of select="link"/>
                    </xsl:attribute>
                    <span class="content"/>
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

</xsl:stylesheet>