<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:import href="common.xsl"/>
    <xsl:import href="header.xsl"/>
    <xsl:import href="footer.xsl"/>

    <xsl:template match="/">
        <html lang="en">
            <head>
                <xsl:copy-of select="$common"/>
                <title><xsl:value-of select="opml/head/title"/></title>
            </head>
            <body>
                <xsl:copy-of select="$header"/>
                <div class="wrapper">

                    <h1><xsl:value-of select="opml/head/title"/></h1>
                    <div class="outlines">
                        <xsl:apply-templates select="//outline"/>
                    </div>

                </div>
                <xsl:copy-of select="$footer"/>
            </body>
        </html>
    </xsl:template>

    <xsl:template match="outline">
        <div class="user">
            <a>
                <xsl:attribute name="href">
                    <xsl:value-of select="@xmlUrl"/>
                </xsl:attribute>
                <b>
                    <xsl:value-of select="@title"/>
                </b>
                <span>
                    (<xsl:value-of select="@text"/>)
                </span>
            </a>
        </div>
    </xsl:template>

</xsl:stylesheet>