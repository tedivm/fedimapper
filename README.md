# FediMapper

This is the project that drives the [FediverseAlmanac](https://www.fediversealmanac.com/docs), a free and open source API for the Fediverse. It has two components- a web crawler that ingests data from all of the Fediverse instances it can find, and a Web API that exposes that data for use.

This API exposes a lot of fun information-

* General [instance metadata](https://www.fediversealmanac.com/docs#/Instances/get_instance).
* [Software and Versions](https://www.fediversealmanac.com/docs#/Software/get_software_stats) on the Fediverse, including [instance lists](https://www.fediversealmanac.com/docs#/Software/get_software_instances).
* [Network Data](https://www.fediversealmanac.com/docs#/Networks/get_network_stats), again including instance lists based on either [Network ID](https://www.fediversealmanac.com/docs#/Networks/get_network_instances) or [Company](https://www.fediversealmanac.com/docs#/Networks/get_company_networks).
* Lists of the [most banned instances](https://www.fediversealmanac.com/docs#/Reputation/get_bans_ranked) in the Fediverse.
* Which instances [ban](https://www.fediversealmanac.com/docs#/Instances/get_instance_bans) or are [banned by](https://www.fediversealmanac.com/docs#/Instances/get_instance_banned_from) other instances.
* [Subdomain Clusters](https://www.fediversealmanac.com/docs#/Reputation/get_subdomain_clusters).

## Why?

The Fediverse needs an API, and I like creating crawlers. The hope is that an easy to use API for the Fediverse will allow people to build tools on top of it- the idea is to reduce the barrier of entry by making it so people do not have to build and run their own web crawlers.


## Block this Bot

Have an instance and don't want us crawling it? Block this bot with your `robots.txt`! We use two separate user agents- `fedimapper` is used by the development version and anyone who clones this repo, while the FediverseAlmanac uses `FediverseAlmanac` for its user agent. To stop both add this to your `robots.txt` file.

```
User-agent: fedimapper
  Disallow: /
User-agent: FediverseAlmanac
  Disallow: /
```


Just want to stop us from reading your block list, but otherwise are okay with metadata being included? Update your `robots.txt` to forbid crawling of your domain blocks endpoint. You can enable this for all crawlers (although I can't promise others will honor it).

```
User-agent: *
  Disallow: /api/v1/instance/domain_blocks
```

## Sponsorship

This project is developed and hosted by [Robert Hafner](https://blog.tedivm.com), who currently pays for it out of pocket. If you find this project useful  please consider sponsoring me using Github!

<center>

[![Github Sponsorship](https://raw.githubusercontent.com/mechPenSketch/mechPenSketch/master/img/github_sponsor_btn.svg)](https://github.com/sponsors/tedivm)

</center>

## Attribution

This project uses several upstream projects and data sources.

* [mastodon.social](https://mastodon.social) and [diasp.org](https://diasp.org) are used to bootstrap the network.
* [Alir3z4's Stop Words](https://github.com/Alir3z4/stop-words) is used to remove noise when processing ban comments for keywords.
* [cymru whois](http://whois.nic.cymru/) is used for network data.

If you use the data in from this site please provide attribution.
