<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:import href="layout.xsl"/>

    <xsl:template match="/">
        <xsl:call-template name="layout"/>
    </xsl:template>

    <xsl:template name="title">
        <link rel="stylesheet" href="/static/css/home.css" />
        <title><xsl:value-of select="//code"/> - <xsl:value-of select="//name"/></title>
    </xsl:template>

    <xsl:template name="panel">
    </xsl:template>

    <xsl:template name="main">
        <h3>
            <span><xsl:value-of select="//code"/></span>
            -
            <span><xsl:value-of select="//name"/></span>
        </h3>
        <div>
            <span><xsl:value-of select="//message"/></span>
        </div>
    </xsl:template>

</xsl:stylesheet>
