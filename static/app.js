"use strict";

// The server puts its day offset (e.g. "+05:00") into the page. All times shown here come
// from the API already in that offset, so we read them from the strings, never via the
// browser's time zone.
const OFFSET = document.querySelector('meta[name="day-tz-offset"]').content;
const PAYMENT = { card: "Карта", cash: "Наличные" };
const MINUTES_IN_DAY = 24 * 60;

const $ = (id) => document.getElementById(id);
const numberFormat = new Intl.NumberFormat("ru-RU");
const money = (value) => numberFormat.format(value);
const dayFormat = new Intl.DateTimeFormat("ru-RU", {
  weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC",
});

const state = {
  day: null,        // "YYYY-MM-DD" currently shown
  requested: null,  // what we asked for last: a date or "today"
  today: null,      // server's today, known after a "today" request
  controller: null, // aborts a stale request when the user flips days quickly
  flashId: null,    // trip to highlight after adding
};

/* ---------- Dates and times (strings only, no browser time zone) ---------- */

function utcDate(day) {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

function shiftDay(day, delta) {
  const date = utcDate(day);
  date.setUTCDate(date.getUTCDate() + delta);
  return date.toISOString().slice(0, 10);
}

function dayTitle(day) {
  return dayFormat.format(utcDate(day)).replace(" г.", "");
}

const clock = (iso) => iso.slice(11, 16);
const minuteOfDay = (iso) => Number(iso.slice(11, 13)) * 60 + Number(iso.slice(14, 16));

function durationMinutes(trip) {
  return Math.round((Date.parse(trip.end) - Date.parse(trip.start)) / 60000);
}

function formatDuration(minutes) {
  if (minutes < 60) return `${minutes} мин`;
  const rest = minutes % 60;
  return rest ? `${Math.floor(minutes / 60)} ч ${rest} мин` : `${minutes / 60} ч`;
}

/* ---------- Loading a day ---------- */

async function load(target, { push = false } = {}) {
  state.requested = target;
  state.controller?.abort();
  const controller = (state.controller = new AbortController());

  // Show the skeleton only if the answer is not instant, so fast loads do not flicker.
  const skeletonTimer = setTimeout(showSkeleton, 120);
  try {
    const response = await fetch(`/api/days/${target}`, { signal: controller.signal });
    if (!response.ok) throw new Error(`Сервер ответил ${response.status}.`);
    const data = await response.json();
    if (target === "today") state.today = data.date;
    render(data);
    const url = `?date=${data.date}`;
    if (push) history.pushState({ date: data.date }, "", url);
    else history.replaceState({ date: data.date }, "", url);
  } catch (error) {
    if (error.name === "AbortError") return;
    showError(error instanceof TypeError ? "Нет соединения с сервером." : error.message);
  } finally {
    clearTimeout(skeletonTimer);
    if (state.controller === controller) $("main").classList.remove("is-loading");
  }
}

function showSkeleton() {
  $("error-state").hidden = true;
  $("content").hidden = false;
  $("main").classList.add("is-loading");
  $("empty-state").hidden = true;
  $("trips").replaceChildren(
    ...Array.from({ length: 3 }, () => {
      const row = document.createElement("li");
      row.className = "skel-row";
      row.setAttribute("aria-hidden", "true");
      row.append(...Array.from({ length: 4 }, () => document.createElement("span")));
      return row;
    })
  );
}

function showError(message) {
  $("main").classList.remove("is-loading");
  $("content").hidden = true;
  $("error-text").textContent = `${message} Проверьте соединение и попробуйте ещё раз.`;
  $("error-state").hidden = false;
  $("retry").focus();
}

/* ---------- Rendering ---------- */

function render(data) {
  state.day = data.date;
  $("error-state").hidden = true;
  $("content").hidden = false;

  $("day-title").textContent = dayTitle(data.date);
  document.title = `${dayTitle(data.date)} — Дневник смен`;
  $("date-input").value = data.date;
  $("today").setAttribute("aria-pressed", String(state.today === data.date));

  renderSummary(data.summary);
  renderTimeline(data.trips, data.date);
  renderList(data.trips, data.date);
}

function renderSummary(summary) {
  const { card, cash } = summary.by_payment;
  $("net").textContent = money(summary.net);
  $("split-card").textContent = money(card.net);
  $("split-cash").textContent = money(cash.net);
  $("m-count").textContent = money(summary.trips_count);
  $("m-revenue").textContent = money(summary.revenue);
  $("m-commission").textContent = money(summary.commission);

  // Bar proportions only; the numbers themselves come from the API.
  const total = card.net + cash.net;
  $("split-card-bar").style.width = total ? `${(card.net / total) * 100}%` : "0";
  $("split-cash-bar").style.width = total ? `${(cash.net / total) * 100}%` : "0";
}

function tripLabel(trip, day) {
  const nextDay = trip.end.slice(0, 10) !== day ? " следующего дня" : "";
  return `${clock(trip.start)}–${clock(trip.end)}${nextDay}, ${PAYMENT[trip.payment]}, ${money(trip.amount)}`;
}

function renderTimeline(trips, day) {
  const track = $("track");
  if (trips.length === 0) {
    const empty = document.createElement("div");
    empty.className = "timeline__empty";
    empty.textContent = "Нет поездок";
    track.replaceChildren(empty);
    return;
  }

  // Overlapping trips go to separate lanes so none hides another.
  const laneEnds = [];
  const placed = trips.map((trip) => {
    const start = minuteOfDay(trip.start);
    const clipped = trip.end.slice(0, 10) !== day; // crosses midnight: cut at 24:00
    const end = clipped ? MINUTES_IN_DAY : minuteOfDay(trip.end);
    let lane = laneEnds.findIndex((laneEnd) => laneEnd <= start);
    if (lane === -1) lane = laneEnds.push(end) - 1;
    else laneEnds[lane] = end;
    return { trip, start, end, clipped, lane };
  });

  const lanes = laneEnds.length;
  track.replaceChildren(
    ...placed.map(({ trip, start, end, clipped, lane }) => {
      const block = document.createElement("button");
      block.type = "button";
      block.className = `block block--${trip.payment}${clipped ? " block--clipped" : ""}`;
      block.dataset.id = trip.id;
      block.style.left = `${(start / MINUTES_IN_DAY) * 100}%`;
      block.style.width = `${((end - start) / MINUTES_IN_DAY) * 100}%`;
      block.style.top = `calc(8px + ${lane} * (100% - 16px) / ${lanes})`;
      block.style.height = `calc((100% - 16px) / ${lanes} - ${lanes > 1 ? 2 : 0}px)`;
      block.setAttribute("aria-label", tripLabel(trip, day) + (clipped ? ", продолжается после полуночи" : ""));
      block.title = `${clock(trip.start)}–${clock(trip.end)} · ${PAYMENT[trip.payment]} · ${money(trip.amount)}`;
      block.addEventListener("click", () => {
        const row = document.querySelector(`.trip[data-id="${CSS.escape(trip.id)}"]`);
        row?.scrollIntoView({ block: "nearest", behavior: "smooth" });
        row?.focus({ preventScroll: true });
      });
      return block;
    })
  );
}

function renderList(trips, day) {
  $("trips-count").textContent = trips.length ? `${trips.length}` : "";
  $("empty-state").hidden = trips.length > 0;

  $("trips").replaceChildren(
    ...trips.map((trip) => {
      const row = document.createElement("li");
      row.className = "trip";
      row.tabIndex = 0;
      row.dataset.id = trip.id;
      row.setAttribute("aria-label", tripLabel(trip, day));

      const time = document.createElement("span");
      time.className = "trip__time";
      time.textContent = `${clock(trip.start)} – ${clock(trip.end)}`;
      if (trip.end.slice(0, 10) !== day) {
        const next = document.createElement("span");
        next.className = "trip__next";
        next.textContent = "след. день";
        time.append(next);
      }

      const amount = document.createElement("span");
      amount.className = "trip__amount";
      amount.textContent = money(trip.amount);

      const meta = document.createElement("span");
      meta.className = "trip__meta";
      meta.textContent = `${formatDuration(durationMinutes(trip))} · ID ${trip.id}`;

      const tag = document.createElement("span");
      tag.className = "tag";
      const swatch = document.createElement("span");
      swatch.className = `swatch swatch--${trip.payment}`;
      tag.append(swatch, PAYMENT[trip.payment]);

      row.append(time, amount, meta, tag);
      return row;
    })
  );

  if (state.flashId) {
    document.querySelector(`.trip[data-id="${CSS.escape(state.flashId)}"]`)?.classList.add("is-new");
    state.flashId = null;
  }
}

/* ---------- Linking timeline blocks and list rows ---------- */

function setLinked(id) {
  document.querySelectorAll(".is-linked").forEach((el) => el.classList.remove("is-linked"));
  if (id) {
    document.querySelectorAll(`[data-id="${CSS.escape(id)}"]`).forEach((el) => el.classList.add("is-linked"));
  }
}

for (const container of [$("track"), $("trips")]) {
  for (const [on, off] of [["mouseover", "mouseout"], ["focusin", "focusout"]]) {
    container.addEventListener(on, (event) => setLinked(event.target.closest("[data-id]")?.dataset.id));
    container.addEventListener(off, () => setLinked(null));
  }
}

/* ---------- Day navigation ---------- */

const go = (target) => load(target, { push: true });

$("prev").addEventListener("click", () => state.day && go(shiftDay(state.day, -1)));
$("next").addEventListener("click", () => state.day && go(shiftDay(state.day, 1)));
$("today").addEventListener("click", () => go("today"));
$("date-input").addEventListener("change", (event) => event.target.value && go(event.target.value));
$("retry").addEventListener("click", () => load(state.requested));
window.addEventListener("popstate", () => load(new URLSearchParams(location.search).get("date") || "today"));

document.addEventListener("keydown", (event) => {
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
  if ($("add-dialog").open || event.target.closest("input, textarea, select")) return;
  if (!state.day) return;
  if (event.key === "ArrowLeft") go(shiftDay(state.day, -1));
  if (event.key === "ArrowRight") go(shiftDay(state.day, 1));
});

/* ---------- Add trip form ---------- */

const dialog = $("add-dialog");
const form = $("add-form");
const FIELDS = ["date", "start", "end", "amount", "commission", "payment", "id"];

// API error -> [form field, Russian text]. Model-level errors only have loc ["body"],
// so the two rules checked across fields are recognised by their message.
function describeError(error) {
  const field = error.loc[1];
  if (error.msg.includes("end must be later than start")) return ["end", "Окончание должно быть позже начала."];
  if (error.msg.includes("commission must not exceed amount")) return ["commission", "Комиссия не может быть больше суммы."];
  if (error.msg.includes("unknown field")) return [null, "Сервер не принял лишние поля."];
  if (!FIELDS.includes(field)) return [null, error.msg];
  const texts = {
    missing: field === "payment" ? "Выберите способ оплаты." : "Заполните поле.",
    int_type: "Введите целое число без пробелов.",
    int_parsing: "Введите целое число без пробелов.",
    greater_than: "Сумма должна быть больше нуля.",
    greater_than_equal: "Не может быть меньше нуля.",
    less_than_equal: "Слишком большое число.",
    string_too_short: "Укажите ID.",
    string_too_long: "ID — не длиннее 64 символов.",
    literal_error: "Выберите «Карта» или «Наличные».",
    datetime_from_date_parsing: "Неверное время.",
    datetime_parsing: "Неверное время.",
  };
  return [field, texts[error.type] || error.msg];
}

function clearErrors() {
  $("form-error").hidden = true;
  for (const name of FIELDS) {
    $(`e-${name}`).textContent = "";
    $(`f-${name}`)?.removeAttribute("aria-invalid");
  }
}

function showFieldError(field, text) {
  if (!field) {
    $("form-error").textContent = text;
    $("form-error").hidden = false;
    return;
  }
  const target = $(`e-${field}`);
  target.textContent = target.textContent ? `${target.textContent} ${text}` : text;
  $(`f-${field}`)?.setAttribute("aria-invalid", "true");
}

function focusFirstError() {
  const first = FIELDS.find((name) => $(`e-${name}`).textContent);
  (first && first !== "payment" ? $(`f-${first}`) : form.querySelector('input[name="payment"]:checked'))?.focus();
}

function newId() {
  const day = ($("f-date").value || state.day || "").replaceAll("-", "").slice(4);
  return `${day}-${Math.random().toString(36).slice(2, 6)}`;
}

function endsNextDay() {
  const start = $("f-start").value;
  const end = $("f-end").value;
  return Boolean(start && end && end < start);
}

function updateEndHint() {
  const hint = $("h-end");
  if (endsNextDay() && $("f-date").value) {
    const next = shiftDay($("f-date").value, 1);
    hint.textContent = `Окончание на следующий день — ${dayTitle(next).split(", ")[1]}.`;
    hint.hidden = false;
  } else {
    hint.hidden = true;
  }
}

function moneyValue(raw) {
  const value = raw.trim();
  if (value === "") return undefined;
  return /^\d+$/.test(value) ? Number(value) : value; // a non-number goes as is: the API explains
}

function buildTrip() {
  const date = $("f-date").value;
  const start = $("f-start").value;
  const end = $("f-end").value;
  const trip = {
    id: $("f-id").value,
    start: date && start ? `${date}T${start}:00${OFFSET}` : undefined,
    end: date && end ? `${endsNextDay() ? shiftDay(date, 1) : date}T${end}:00${OFFSET}` : undefined,
    amount: moneyValue($("f-amount").value),
    payment: form.querySelector('input[name="payment"]:checked')?.value,
    commission: moneyValue($("f-commission").value),
  };
  return JSON.parse(JSON.stringify(trip)); // drops undefined: the API reports missing fields
}

function openDialog() {
  if (!$("f-id").value) {
    $("f-date").value = state.day || "";
    $("f-id").value = newId();
  }
  clearErrors();
  updateEndHint();
  dialog.showModal();
  $("f-start").focus();
}

function toast(text) {
  const box = $("toast");
  box.textContent = text;
  box.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (box.hidden = true), 3500);
}

$("add-open").addEventListener("click", openDialog);
$("empty-add").addEventListener("click", openDialog);
$("new-id").addEventListener("click", () => ($("f-id").value = newId()));
for (const id of ["f-start", "f-end", "f-date"]) $(id).addEventListener("input", updateEndHint);
dialog.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => dialog.close()));
dialog.addEventListener("click", (event) => event.target === dialog && dialog.close());

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearErrors();
  const submit = $("add-submit");
  submit.disabled = true;
  submit.textContent = "Сохраняю…";

  try {
    const response = await fetch("/api/trips", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildTrip()),
    });
    const body = await response.json().catch(() => null);

    if (response.status === 201 || response.status === 200) {
      dialog.close();
      toast(response.status === 201 ? "Поездка добавлена" : "Уже сохранено, дубля нет");
      state.flashId = body.id;
      await go(body.start.slice(0, 10));
    } else if (response.status === 409) {
      showFieldError("id", "Поездка с таким ID уже есть, и её данные другие. Проверьте поля или нажмите «Новый ID».");
    } else if (response.status === 422 && Array.isArray(body?.detail)) {
      body.detail.forEach((error) => showFieldError(...describeError(error)));
    } else {
      showFieldError(null, `Сервер ответил ошибкой ${response.status}. Попробуйте ещё раз.`);
    }
  } catch {
    showFieldError(null, "Нет соединения с сервером. Данные в форме сохранены — попробуйте ещё раз.");
  } finally {
    submit.disabled = false;
    submit.textContent = "Сохранить";
    if (dialog.open) focusFirstError();
  }
});

/* ---------- Start ---------- */

load(new URLSearchParams(location.search).get("date") || "today");
