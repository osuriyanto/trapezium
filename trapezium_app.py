
# trapezium_app.py
import io
import matplotlib.pyplot as plt
import streamlit as st

# ==== Your plotting function (minor fix: return values, not print) ====

def plot_fcess_trapezium(
    facility, market,
    orig_min, orig_max, orig_low_bp, orig_high_bp, max_service_qty,
    adj_min, adj_max, adj_low_bp, adj_high_bp, adj_service_qty=None,
    *, contain_within_original=True, tol=1e-6, ax=None
):
    """
    Draw original (solid blue) and adjusted (dashed orange) shapes.
    Returns (reduced_service_qty, service_qty_reduction).
    """
    class _LabelRegistry:
        def __init__(self, tol=1e-6):
            self.tol, self._p = tol, []
        def _seen(self, x, y):
            return any(abs(px - x) <= self.tol and abs(py - y) <= self.tol for px, py in self._p)
        def place(self, ax, x, y, text, offset=(6, 6)):
            if not self._seen(x, y):
                ax.annotate(text, (x, y), textcoords="offset points", xytext=offset, fontsize=8)
                self._p.append((x, y))

    H = float(max_service_qty)
    if adj_service_qty is None:
        adj_service_qty = H

    # Keep adjusted inside original envelope
    if contain_within_original:
        adj_min = max(adj_min, orig_min)
        adj_max = min(adj_max, orig_max)
        adj_low_bp = min(adj_low_bp, orig_low_bp)
        adj_high_bp = min(adj_high_bp, orig_high_bp)
        adj_service_qty = min(adj_service_qty, H)

    # Enforce ordering
    adj_min = min(max(adj_min, orig_min), orig_low_bp)
    adj_low_bp = min(max(adj_low_bp, adj_min), orig_low_bp)
    adj_high_bp = min(max(adj_high_bp, adj_low_bp), orig_high_bp)
    adj_max = min(max(adj_max, adj_high_bp), orig_max)

    left_slanted = abs(orig_low_bp - orig_min) > tol
    right_slanted = abs(orig_high_bp - orig_max) > tol

    heights = []
    if right_slanted:
        denom = (orig_max - orig_high_bp)
        if abs(denom) > tol:
            height_right = H * (adj_max - adj_high_bp) / denom
            heights.append(max(0.0, min(height_right, H)))
    if left_slanted:
        # keep right side vertical, share left slanted side
        adj_high_bp = adj_max
        denom = (orig_low_bp - orig_min)
        if abs(denom) > tol:
            height_left = H * (adj_low_bp - adj_min) / denom
            heights.append(max(0.0, min(height_left, H)))

    if heights:
        adj_service_qty = min(min(heights), adj_service_qty)
    adj_service_qty = max(0.0, min(adj_service_qty, H))

    orig_poly = [(orig_min, 0), (orig_max, 0), (orig_high_bp, H), (orig_low_bp, H)]
    adj_poly = [(adj_min, 0), (adj_max, 0), (adj_high_bp, adj_service_qty), (adj_low_bp, adj_service_qty)]

    created_fig = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 5))
        created_fig = True
    reg = _LabelRegistry(tol=1e-4)

    def _poly(ax, pts, edge, face, ls='-'):
        xs, ys = zip(*(pts + [pts[0]]))
        ax.plot(xs, ys, ls=ls, color=edge, lw=2)
        ax.fill(xs, ys, facecolor=face, alpha=0.2, edgecolor='none')

    _poly(ax, orig_poly, 'tab:blue', 'tab:blue', '-')
    _poly(ax, adj_poly, 'tab:orange', 'tab:orange', '--')

    # Labels with dedupe
    for x, y, t, c in [
        (orig_min, 0, f"min={orig_min:g}", 'tab:blue'),
        (orig_max, 0, f"max={orig_max:g}", 'tab:blue'),
        (orig_low_bp, H, f"low_bp={orig_low_bp:g}, H={H:g}", 'tab:blue'),
        (orig_high_bp, H, f"high_bp={orig_high_bp:g}, H={H:g}", 'tab:blue'),
        (adj_min, 0, f"adj_min={adj_min:g}", 'tab:orange'),
        (adj_max, 0, f"adj_max={adj_max:g}", 'tab:orange'),
        (adj_low_bp, adj_service_qty, f"adj_low_bp={adj_low_bp:g}, h={adj_service_qty:g}", 'tab:orange'),
        (adj_high_bp, adj_service_qty, f"adj_high_bp={adj_high_bp:g}, h={adj_service_qty:g}", 'tab:orange'),
    ]:
        if not reg._seen(x, y):
            ax.plot([x], [y], marker='o', ms=4, color=c)
            reg.place(ax, x, y, t)

    ax.set_title(f"{facility}: {market} FCESS trapezium")
    ax.set_xlabel("Enablement / Breakpoints (MW)")
    ax.set_ylabel("Service quantity (MW)")
    xmin, xmax = min(orig_min, adj_min), max(orig_max, adj_max)
    span = (xmax - xmin) or 1
    ax.set_xlim(xmin - 0.05 * span, xmax + 0.05 * span)
    ax.set_ylim(0, H * 1.1 if H > 0 else 1)
    ax.plot([], [], color='tab:blue', lw=2, ls='-', label='original')
    ax.plot([], [], color='tab:orange', lw=2, ls='--', label='adjusted')
    ax.legend()
    ax.grid(True, alpha=0.15)

    reduced_service_qty = service_qty_reduction = None
    if adj_service_qty + tol < H:
        reduced_service_qty = adj_service_qty
        service_qty_reduction = H - adj_service_qty
        ax.axhline(adj_service_qty, color='tab:orange', lw=1, ls=':')
        reg.place(ax, xmin, adj_service_qty, f"reduced service quantity = {adj_service_qty:g}", offset=(6, -12))

    # Return values; do NOT print here
    return reduced_service_qty, service_qty_reduction


# ==== Streamlit UI ====

def main():
    st.set_page_config(page_title="FCESS Trapezium", layout="centered")
    st.title("FCESS Trapezium Visualisation")

    with st.sidebar:
        st.header("General")
        facility = st.text_input("Facility name", value="Facility name")
        market = st.text_input("FCESS market", value="Market type")
        contain = st.checkbox("Contain adjusted within original", value=True)
        tol = st.number_input("Tolerance", value=1e-6, min_value=0.0, format="%.6f")
        st.markdown("---")
        st.caption("Tip: Use tab to move through inputs quickly.")

    st.subheader("Original inputs")
    col1, col2, col3 = st.columns(3)
    with col1:
        orig_min = st.number_input("Standing enablement min (MW)", value=0.0)
    with col2:
        orig_low_bp = st.number_input("Standing low breakpoint (MW)", value=30.0)
    with col3:
        max_service_qty = st.number_input("Max service quantity H (MW)", value=40.0, min_value=0.0)

    col4, col5 = st.columns(2)
    with col4:
        orig_high_bp = st.number_input("Standing high breakpoint (MW)", value=90.0)
    with col5:
        orig_max = st.number_input("Standing enablement max (MW)", value=120.0)

    st.subheader("Adjusted inputs")
    col6, col7, col8 = st.columns(3)
    with col6:
        adj_min = st.number_input("Adjusted enablement min (MW)", value=10.0)
    with col7:
        adj_low_bp = st.number_input("Adjusted low breakpoint (MW)", value=20.0)
    with col8:
        adj_service_qty = st.number_input("Adjusted service quantity h (MW)\n(blank = compute via slopes)", value=max_service_qty, min_value=0.0)

    col9, col10 = st.columns(2)
    with col9:
        adj_high_bp = st.number_input("Adjusted high breakpoint (MW)", value=80.0)
    with col10:
        adj_max = st.number_input("Adjusted enablement max (MW)", value=110.0)

    # Validate ordering of original inputs
    errs = []
    if not (orig_min <= orig_low_bp <= orig_high_bp <= orig_max):
        errs.append("Original must satisfy: min ≤ low_bp ≤ high_bp ≤ max")

    if errs:
        for e in errs:
            st.error(e)
        st.stop()

    # Single render zone to avoid duplicate widgets
    result = st.container()

    plot_btn = st.button("Plot trapeziums", key="plot")

    if plot_btn:
        with result:
            fig, ax = plt.subplots(figsize=(8, 5))
            reduced, reduction = plot_fcess_trapezium(
                facility, market,
                orig_min, orig_max, orig_low_bp, orig_high_bp, max_service_qty,
                adj_min, adj_max, adj_low_bp, adj_high_bp, adj_service_qty,
                contain_within_original=contain, tol=tol, ax=ax
            )

            # Save BEFORE rendering and reset buffer so downloads aren't empty
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
            buf.seek(0)

            st.pyplot(fig, clear_figure=True)

            c1, c2 = st.columns(2)
            if reduced is not None:
                c1.metric("Reduced service qty (MW)", f"{reduced:.3f}")
                c2.metric("Service qty reduction (MW)", f"{reduction:.3f}")
            else:
                st.info("No FCESS max service quantity reduction.")

            # Exactly one download button, unique key
            st.download_button(
                "Download plot (PNG)", data=buf,
                file_name=f"{facility}_{market}_trapezium.png", mime="image/png",
                key="download_png_unique"
            )
        st.pyplot(fig, clear_figure=True)
        
if __name__ == "__main__":
    main()

