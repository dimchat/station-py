<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:import href="common.xsl"/>
    <xsl:import href="header.xsl"/>
    <xsl:import href="footer.xsl"/>

    <xsl:template match="/">
        <html lang="en">
            <head>
                <xsl:copy-of select="$common"/>
                <title><xsl:value-of select="message/content/title"/></title>
            </head>
            <body>
                <xsl:copy-of select="$header"/>
                <div class="wrapper">

                    <h3>
                        <span>Error: </span>
                        <span><xsl:value-of select="result/code"/></span>
                    </h3>
                    <div>
                        <span><xsl:value-of select="result/message"/></span>
                    </div>

                </div>
                <xsl:copy-of select="$footer"/>
            </body>
        </html>
    </xsl:template>

</xsl:stylesheet>
