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
                <title><xsl:value-of select="message/content/title"/></title>
            </head>
            <body>
                <h1><xsl:value-of select="message/content/title"/></h1>
                <div>
                    <span><b>Sender</b>: </span>
                    <span><xsl:value-of select="message/envelope/sender"/></span>
                </div>
                <div>
                    <span><b>Time</b>: </span>
                    <span><xsl:value-of select="message/envelope/time"/></span>
                </div>
                <div>
                    <div><b>Content</b>: </div>
                    <div><xsl:value-of select="message/content/text"/></div>
                </div>
            </body>
        </html>

    </xsl:template>
</xsl:stylesheet>
