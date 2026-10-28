/* One select primitive for fields, compact controls, and filters. Native selects
   remain the data/form owners and the no-JavaScript fallback. */
(function (root) {
  const instances = new Map();
  let opened = null,
    typeBuffer = "",
    typeTimer;
  function close(restoreFocus = false) {
    if (!opened) return;
    const current = opened;
    opened = null;
    if (current.menu.matches(":popover-open")) current.menu.hidePopover();
    current.button.setAttribute("aria-expanded", "false");
    if (restoreFocus) current.button.focus();
  }
  function position(current) {
    const rect = current.button.getBoundingClientRect();
    const margin = 10,
      width = Math.min(Math.max(rect.width, 190), innerWidth - 2 * margin);
    const below = innerHeight - rect.bottom - margin,
      above = rect.top - margin;
    const height = Math.min(280, Math.max(below, above) - 8);
    const flip =
      below < Math.min(current.menu.scrollHeight, 220) && above > below;
    current.menu.style.width = width + "px";
    current.menu.style.maxHeight = Math.max(100, height) + "px";
    current.menu.style.left =
      Math.max(margin, Math.min(rect.left, innerWidth - width - margin)) + "px";
    current.menu.style.top = flip ? "auto" : rect.bottom + 6 + "px";
    current.menu.style.bottom = flip
      ? innerHeight - rect.top + 6 + "px"
      : "auto";
  }
  function syncOne(current) {
    const select = current.select;
    current.label.textContent =
      select.selectedOptions[0]?.textContent || "Choose an option";
    current.button.disabled = select.disabled;
    current.menu.replaceChildren();
    [...select.options].forEach((option, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.role = "option";
      button.id = select.id + "-option-" + index;
      button.dataset.index = String(index);
      button.setAttribute("aria-selected", String(option.selected));
      button.disabled = option.disabled;
      button.tabIndex = option.selected ? 0 : -1;
      const label = document.createElement("span");
      label.textContent = option.textContent;
      const check = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "svg",
      );
      check.setAttribute("class", "icon");
      check.setAttribute("aria-hidden", "true");
      check.setAttribute("viewBox", "0 0 24 24");
      const path = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "path",
      );
      path.setAttribute("d", "m5 12 4 4L19 6");
      check.append(path);
      button.append(label, check);
      button.addEventListener("click", () => {
        select.selectedIndex = index;
        select.dispatchEvent(new Event("input", { bubbles: true }));
        select.dispatchEvent(new Event("change", { bubbles: true }));
        syncOne(current);
        close(true);
      });
      current.menu.append(button);
    });
  }
  function open(current, last = false) {
    if (current.button.disabled) return;
    close();
    syncOne(current);
    opened = current;
    current.menu.showPopover();
    position(current);
    current.button.setAttribute("aria-expanded", "true");
    const options = [
      ...current.menu.querySelectorAll("[role=option]:not(:disabled)"),
    ];
    const selected = options.find(
      (o) => o.getAttribute("aria-selected") === "true",
    );
    const target = selected || options[last ? options.length - 1 : 0];
    target?.focus({ preventScroll: true });
    target?.scrollIntoView({ block: "nearest" });
  }
  function enhance(select) {
    if (instances.has(select) || !select.id || select.multiple) return;
    const shell = document.createElement("div");
    shell.className = "select-shell";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "select-trigger";
    button.id = select.id + "-trigger";
    button.setAttribute("aria-haspopup", "listbox");
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-controls", select.id + "-options");
    const fieldLabel = document.querySelector(`label[for="${select.id}"]`);
    if (fieldLabel) {
      fieldLabel.id ||= select.id + "-label";
      button.setAttribute(
        "aria-labelledby",
        fieldLabel.id + " " + select.id + "-value",
      );
      fieldLabel.addEventListener("click", (event) => {
        event.preventDefault();
        button.focus();
      });
    } else
      button.setAttribute(
        "aria-label",
        select.getAttribute("aria-label") || "Choose an option",
      );
    const label = document.createElement("span");
    label.className = "select-value";
    label.id = select.id + "-value";
    const chevron = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "svg",
    );
    chevron.setAttribute("class", "icon select-chevron");
    chevron.setAttribute("viewBox", "0 0 24 24");
    chevron.setAttribute("aria-hidden", "true");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", "m7 10 5 5 5-5");
    chevron.append(path);
    button.append(label, chevron);
    const menu = document.createElement("div");
    menu.className = "select-options";
    menu.id = select.id + "-options";
    menu.setAttribute("popover", "manual");
    menu.role = "listbox";
    menu.setAttribute(
      "aria-label",
      fieldLabel?.textContent.trim() ||
        select.getAttribute("aria-label") ||
        "Options",
    );
    select.before(shell);
    shell.append(select, button, menu);
    select.classList.add("enhanced-select");
    select.tabIndex = -1;
    select.setAttribute("aria-hidden", "true");
    const current = { select, button, label, menu };
    instances.set(select, current);
    syncOne(current);
    button.addEventListener("click", () =>
      opened === current ? close() : open(current),
    );
    button.addEventListener("keydown", (event) => {
      if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
        event.preventDefault();
        open(current, event.key === "End" || event.key === "ArrowUp");
      }
    });
    menu.addEventListener("keydown", (event) => {
      const options = [
        ...menu.querySelectorAll("[role=option]:not(:disabled)"),
      ];
      const index = options.indexOf(document.activeElement);
      let next;
      if (event.key === "ArrowDown") next = (index + 1) % options.length;
      else if (event.key === "ArrowUp")
        next = (index + options.length - 1) % options.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = options.length - 1;
      else if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        close(true);
        return;
      } else if (event.key === "Tab") {
        close(true);
        return;
      } else if (
        event.key.length === 1 &&
        !event.ctrlKey &&
        !event.metaKey &&
        ![" ", "Enter"].includes(event.key)
      ) {
        clearTimeout(typeTimer);
        typeBuffer += event.key.toLowerCase();
        typeTimer = setTimeout(() => (typeBuffer = ""), 650);
        next = options.findIndex((o) =>
          o.textContent.toLowerCase().startsWith(typeBuffer),
        );
      } else return;
      if (next >= 0) {
        event.preventDefault();
        options[next]?.focus();
      }
    });
    select.addEventListener("change", () => syncOne(current));
    new MutationObserver(() => syncOne(current)).observe(select, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["disabled", "label"],
    });
  }
  function init() {
    document.querySelectorAll("select").forEach(enhance);
    document.addEventListener(
      "pointerdown",
      (event) => {
        if (
          opened &&
          !opened.menu.contains(event.target) &&
          !opened.button.contains(event.target)
        )
          close();
      },
      true,
    );
    window.addEventListener("resize", () => opened && position(opened));
    document.addEventListener(
      "scroll",
      (event) => {
        if (
          opened &&
          event.target !== opened.menu &&
          !opened.menu.contains(event.target)
        )
          close();
      },
      true,
    );
    document
      .querySelectorAll("dialog")
      .forEach((d) => d.addEventListener("close", () => close()));
  }
  root.ScholarControls = {
    init,
    close,
    sync() {
      instances.forEach(syncOne);
    },
  };
})(window);
