"""
Multibagger engine - hosted view.

Runs on Streamlit Community Cloud, reading whatever the local engine last
pushed to the repo. Deploy once; it redeploys itself on every push.

ON "24x7". The APP is always reachable. The DATA is only as fresh as the last
push from your machine, which runs 11:00-19:00. So this is a window onto the
engine, not a second engine - and the header says plainly how old what you are
looking at is, because a stale dashboard that looks live is worse than one that
is obviously stale.

Nothing here computes a signal. Every number was produced locally, where the
price panel and the full archive live. This renders what the engine decided.
"""

from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs")

st.set_page_config(page_title="Multibagger Engine", page_icon="📡",
                   layout="wide", initial_sidebar_state="collapsed")


def _path(name: str) -> str | None:
    for d in (DOCS, HERE):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def _age(p: str | None) -> tuple[str, float]:
    if not p:
        return "missing", 1e9
    h = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(p))
         ).total_seconds() / 3600
    if h < 1:
        return "just now", h
    if h < 24:
        return f"{h:.0f}h ago", h
    return f"{h/24:.0f}d ago", h


def _embed(path: str | None, height: int, label: str):
    if not path:
        st.warning(f"{label} has not been published yet. Run `publish.py` on "
                   f"the machine running the engine.")
        return
    with open(path, encoding="utf-8") as fh:
        components.html(fh.read(), height=height, scrolling=True)


# ---------------------------------------------------------------------------

cockpit = _path("cockpit.html")
dash = _path("dashboard.html")
rank = _path("ranking.csv")

c_age, c_h = _age(cockpit)
d_age, _ = _age(dash)

left, right = st.columns([3, 2])
with left:
    st.markdown("### 📡 Multibagger Engine")
    st.caption("Shadow mode · research use, not investment advice")
with right:
    st.markdown(
        f"<div style='text-align:right;color:#8b93a7;font-size:13px;'>"
        f"cockpit <b>{c_age}</b> &nbsp;·&nbsp; dashboard <b>{d_age}</b></div>",
        unsafe_allow_html=True)

# A stale page that looks live is the failure mode worth guarding against.
if c_h > 24 * 9:
    st.error(f"Data is {c_age}. The engine has not published for over a week - "
             f"check whether it is still running on your machine.")
elif c_h > 24 * 3:
    st.warning(f"Data is {c_age}. Expected a fresh publish every Sunday.")

tab1, tab2, tab3 = st.tabs(["Cockpit", "Filing dashboard", "Ranking"])

with tab1:
    # Taller again: the movement board sits above the layer boxes and the
    # health card above the hero, so the first screenful is now two cards
    # deep before the per-company detail starts.
    _embed(cockpit, 2400, "The cockpit")

with tab2:
    _embed(dash, 1400, "The filing dashboard")

with tab3:
    if not rank:
        st.info("No ranking published yet.")
    else:
        df = pd.read_csv(rank)
        if "exclude" in df.columns:
            tradeable = df[~df["exclude"].astype(bool)]
            st.caption(f"{len(tradeable):,} tradeable of {len(df):,} ranked. "
                       f"Excluded names are pledged, illiquid, or outside the "
                       f"₹100–3,000cr band.")
        else:
            tradeable = df

        c1, c2, c3 = st.columns([2, 1, 1])
        q = c1.text_input("Filter by symbol", "")
        n = c2.selectbox("Show", [25, 50, 100, 250], index=0)
        only_sweet = c3.checkbox("Entry band only", value=False)

        view = tradeable
        if q:
            view = view[view["symbol"].str.contains(q.strip(), case=False,
                                                    na=False)]
        if only_sweet and "entry_stage" in view.columns:
            view = view[view["entry_stage"] == "sweet"]

        cols = [c for c in ["rank", "symbol", "price", "market_cap_cr",
                            "composite_score", "entry_stage", "years_listed",
                            "peer_group", "peer_breadth", "group_momentum",
                            "stock_momentum", "piotroski", "why_not"]
                if c in view.columns]
        st.dataframe(view[cols].head(n), use_container_width=True,
                     hide_index=True)

        with st.expander("What the columns mean"):
            st.markdown("""
| Column | Meaning |
|---|---|
| `entry_stage` | How far the move has run. **sweet** = up 50–150%, the band measured at +10.6pp forward return |
| `years_listed` | 3–6 years had the highest 3x rate (38.2%) and 1.2% wipeout; under 3 years, 13.7% wipeout |
| `peer_breadth` | Share of the stock's peer group also advancing. Above 70% carried a 5.9% wipeout rate against 8.2% overall |
| `group_momentum` | Six-month return of the peer group's median member |
| `why_not` | Why an excluded name was cut |

The composite does **not** include years_listed or peer_breadth — those are
read alongside it, not folded in.
""")

st.divider()
st.caption(
    "Alerts are exchange filings, public the moment they land. The engine "
    "measures whether its filter selects informative events — not whether they "
    "could have been traded. Momentum carries a measured but modest edge "
    "(t = 5.4); the composite scores AUC ≈ 0.52.")
