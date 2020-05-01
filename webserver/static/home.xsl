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
            <xsl:apply-templates select="//outline"/>
        </div>
    </xsl:template>

    <xsl:template name="main">
        <div id="headlines">

        </div>
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