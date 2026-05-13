# Grounded Intelligence Plugins

Public plugin marketplace for [Grounded Intelligence](https://groundedintelligence.io) client tooling.

## What's here

| Plugin | Skills | Description | Client |
|---|---|---|---|
| `lee-internal-comps` | `internal-comps` | Internal (Dealius) and external (CoStar) lease & sale comps. Internal produces Excel + email drafts. External CoStar comps are reachable via typed MCP tools (`search_external_sale_comps`, `search_external_lease_comps`, `get_external_comp_detail`), backed by a weekly Excel ingest from Will. A broker-facing external-comps skill is forthcoming. | Lee & Associates |

## Install

In Claude Cowork: **Customize → Plugins → Add marketplace** and paste:

```
davidmshaner-gi/gi-plugins
```

Then click **Install** on the plugin you've been authorized for.

## Authorization

Plugins in this marketplace require client-specific authorization. If you haven't been pre-provisioned in the relevant client's broker registry, contact `david@groundedintelligence.io`.
