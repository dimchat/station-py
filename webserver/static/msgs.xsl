<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:template match="/">

        <html lang="en">
            <head>
                <meta charset="UTF-8" />
                <meta http-equiv="X-UA-Compatible" content="IE=Edge" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <meta name="description" content="DIMP Client" />
                <meta name="author" content="Albert Moky" />
                <title><xsl:value-of select="rss/channel/title"/></title>
            </head>
            <body>
                <h1><xsl:value-of select="rss/channel/title"/></h1>
                <div><xsl:value-of select="rss/channel/description"/></div>
                <ul>
                    <xsl:for-each select="rss/channel/item">
                        <li>
                            <a>
                                <xsl:attribute name="href">
                                    <xsl:value-of select="link"/>
                                </xsl:attribute>
                                <xsl:value-of select="title"/>
                            </a>
                        </li>
                    </xsl:for-each>
                </ul>
            </body>
        </html>

    </xsl:template>
</xsl:stylesheet>
