# Butt Hurt Report

Taken and adapted from [here](https://www.itstactical.com/wp-content/uploads/2012/10/ITS_TACTICAL_BUTT_HURT_REPORT1.pdf). Use it at your own risk.

## Querystring support

Simply append something like the following and the form should pre-populate and stream back either a JPG or PDF.

```text
https://butthurt.gooblygock.com/?p1a=Donald%20J%20Trump&p1b=555116969&p1c=2025-10-18&p1d=White%20House&p1e=President&p2a=2025-10-19&p2b=09:00&p2c=No%20Kings%20Rally&p2d=Americans&p2e=MAGA&p31=both&p32=yes&p33=multiple&p34=yes&p41=1&p42=1&p43=1&p44=1&p45=1&p46=1&p47=1&p48=1&p49=1&p410=1&p411=1&p412=1&p413=1&p414=1&p415=1&p5=NKR%20hates%20Murica&export=jpg
```

## Asset optimization

Install dependencies once with `npm install`, then run `npm run build` to generate a minified copy of the static site in `www-optimized/` (HTML, CSS, and JS are minified while other assets are copied verbatim).

## License

Released under the Do Whatever The Fuck You Want License. See `LICENSE`.
