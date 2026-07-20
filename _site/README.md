This is the website of Terrence Gillespie
Its built using Jeykll and hosted on Github pages
Hand crafted, with some quirks, there is no database and it generates static pages.
Hit me up if you have any questions about the setup, archive or want something similar
Have a nice day :]

## Local dev

Quickest path (no Ruby, no Jekyll — fine for `/airlie/` since it's static):

    npm run dev          # whole repo at http://localhost:4000
    npm run dev:airlie   # just the template at http://localhost:4001

No Node? Use Python:

    npm run dev:py       # http://localhost:4000

Full Jekyll build (needed for the markdown-rendered home/archive pages):

    bundle install
    npm run dev:jekyll   # http://localhost:4000

The editor lives at `/airlie/?edit=1` once the server is up.

