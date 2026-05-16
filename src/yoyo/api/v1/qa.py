from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.api.deps import get_db_session
from yoyo.api.responses import success_response
from yoyo.modules.qa.schemas import QAAskRequest
from yoyo.modules.qa.service import ask_question, preview_qa_request

# QA API 的入口文件。
# 这个文件本身很薄，主要职责是：收请求 -> 调用 QA service -> 返回统一响应。
router = APIRouter(prefix="/qa")


@router.get("/playground", response_class=HTMLResponse)
async def qa_playground_page() -> str:
    return _render_qa_playground_html()


@router.post("/preview")
async def preview_qa(
    payload: QAAskRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    preview = await preview_qa_request(session, payload)
    return success_response(preview)


# QA 的主入口：接收用户问题，并交给问答编排层处理。
@router.post("/ask")
async def ask_qa(
    payload: QAAskRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    response = await ask_question(session, payload)
    return success_response(response.model_dump())


def _render_qa_playground_html() -> str:
    return """<!DOCTYPE html>
<html lang=\"zh-CN\">
  <head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>Yoyo QA Playground</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f5f7fb;
        --card: #ffffff;
        --line: #d7dfeb;
        --text: #1f2937;
        --muted: #667085;
        --primary: #2563eb;
        --primary-soft: #dbeafe;
        --success: #0f766e;
        --warning: #b45309;
        --danger: #b91c1c;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif;
        background: var(--bg);
        color: var(--text);
      }
      .page {
        max-width: 1480px;
        margin: 0 auto;
        padding: 24px;
      }
      h1, h2, h3 { margin: 0; }
      p { line-height: 1.5; }
      .hero {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: flex-start;
        margin-bottom: 20px;
      }
      .hero-copy { max-width: 860px; }
      .hero p { color: var(--muted); margin: 10px 0 0; }
      .grid {
        display: grid;
        grid-template-columns: minmax(420px, 520px) minmax(420px, 1fr);
        gap: 20px;
        align-items: start;
      }
      .column { display: grid; gap: 16px; }
      .card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 18px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
      }
      .card h2 {
        font-size: 18px;
        margin-bottom: 6px;
      }
      .subtle {
        color: var(--muted);
        font-size: 13px;
      }
      .field-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
      }
      .field-grid.triple {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }
      .field-grid.single {
        grid-template-columns: 1fr;
      }
      label {
        display: grid;
        gap: 6px;
        font-size: 13px;
        color: var(--muted);
        margin-top: 12px;
      }
      input, select, textarea, button {
        font: inherit;
      }
      input, select, textarea {
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 10px 12px;
        background: #fff;
        color: var(--text);
      }
      textarea {
        min-height: 92px;
        resize: vertical;
      }
      .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 18px;
      }
      button {
        border: 0;
        border-radius: 10px;
        padding: 11px 14px;
        cursor: pointer;
        transition: transform 0.05s ease, opacity 0.2s ease;
      }
      button:hover { opacity: 0.95; }
      button:active { transform: translateY(1px); }
      .primary { background: var(--primary); color: white; }
      .secondary { background: #111827; color: white; }
      .ghost { background: #eef2ff; color: #3730a3; }
      .badge-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 12px;
      }
      .badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 10px;
        border-radius: 999px;
        background: var(--primary-soft);
        color: #1d4ed8;
        font-size: 12px;
      }
      .status {
        margin-top: 12px;
        font-size: 13px;
        color: var(--muted);
      }
      .panel-title {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        margin-bottom: 10px;
      }
      .tabs {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 12px;
      }
      .tab {
        background: #f3f4f6;
        color: #374151;
        padding: 8px 12px;
        border-radius: 999px;
        font-size: 13px;
        border: 1px solid transparent;
      }
      .tab.active {
        background: #e0e7ff;
        color: #3730a3;
        border-color: #c7d2fe;
      }
      .result-box {
        min-height: 220px;
        background: #0f172a;
        color: #e2e8f0;
        border-radius: 12px;
        padding: 14px;
        overflow: auto;
        white-space: pre-wrap;
        word-break: break-word;
        font-size: 13px;
        line-height: 1.5;
      }
      .summary-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
        margin-top: 14px;
      }
      .summary-card {
        background: #f8fafc;
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 12px;
      }
      .summary-card h3 {
        font-size: 13px;
        color: var(--muted);
        margin-bottom: 8px;
      }
      .summary-list {
        display: grid;
        gap: 6px;
        font-size: 13px;
      }
      .summary-item {
        display: flex;
        justify-content: space-between;
        gap: 12px;
      }
      .summary-item span:last-child {
        color: var(--text);
        text-align: right;
        word-break: break-word;
      }
      .answer-box {
        min-height: 120px;
        background: #f8fafc;
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 14px;
        white-space: pre-wrap;
        line-height: 1.6;
      }
      .hint-list {
        margin: 10px 0 0;
        padding-left: 18px;
        color: var(--muted);
      }
      .split {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
      }
      .tiny { font-size: 12px; color: var(--muted); }
      .sticky {
        position: sticky;
        top: 18px;
      }
      @media (max-width: 1100px) {
        .grid { grid-template-columns: 1fr; }
        .sticky { position: static; }
      }
      @media (max-width: 760px) {
        .field-grid, .field-grid.triple, .split { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <div class=\"page\">
      <div class=\"hero\">
        <div class=\"hero-copy\">
          <h1>Yoyo QA Playground</h1>
          <p>用于联调当前 QA 主链路：翻译预处理、意图路由、session-aware 上下文、SQL/RAG 取数，以及最终回答。页面里的配置会写入 <span class=\"mono\">context.qa_playground</span>，并尽量真实影响 prompt 变量。</p>
        </div>
        <div class=\"badge-row\">
          <span class=\"badge\">POST /api/v1/qa/ask</span>
          <span class=\"badge\">POST /api/v1/qa/preview</span>
        </div>
      </div>

      <div class=\"grid\">
        <div class=\"column\">
          <div class=\"card sticky\">
            <div class=\"panel-title\">
              <div>
                <h2>请求配置</h2>
                <div class=\"subtle\">默认只发送最小 QA payload；只有你填写或切换 preset 后，才会把 playground override 注入后端。</div>
              </div>
            </div>

            <label>
              用户问题
              <textarea id=\"query\">请简短介绍一下故宫。</textarea>
            </label>

            <div class=\"field-grid\">
              <label>
                用户语言
                <select id=\"language\">
                  <option value=\"zh\" selected>zh</option>
                  <option value=\"en\">en</option>
                  <option value=\"ms\">ms</option>
                  <option value=\"fil\">fil</option>
                  <option value=\"my\">my</option>
                  <option value=\"km\">km</option>
                  <option value=\"lo\">lo</option>
                  <option value=\"vi\">vi</option>
                </select>
              </label>
              <label>
                user_id
                <input id=\"userId\" placeholder=\"可选\" />
              </label>
            </div>

            <div class=\"field-grid\">
              <label>
                guide_session_id
                <input id=\"guideSessionId\" placeholder=\"已有 session 时填写\" />
              </label>
              <label>
                market
                <input id=\"market\" value=\"beijing\" placeholder=\"默认 beijing\" />
              </label>
            </div>

            <div class=\"field-grid\">
              <label>
                llm_provider override
                <input id=\"llmProvider\" placeholder=\"如 volcengine\" />
              </label>
              <label>
                llm_model override
                <input id=\"llmModel\" placeholder=\"如 doubao-seed-2-0-mini-260428\" />
              </label>
            </div>

            <label>
              快速场景
              <select id=\"preset\">
                <option value=\"default\" selected>默认：最小请求，不注入 override</option>
                <option value=\"trip\">trip_assistant：当前站点 / 下一站</option>
                <option value=\"translation\">translation：翻给工作人员看</option>
                <option value=\"weather\">weather：天气 fallback / 城市上下文</option>
                <option value=\"navigation\">navigation：多段文字导航</option>
              </select>
            </label>

            <h3 style=\"margin-top:20px;\">行程 / Session 变量覆盖</h3>
            <div class=\"field-grid triple\">
              <label>
                current_stop_name
                <input id=\"currentStopName\" placeholder=\"如 天安门广场\" />
              </label>
              <label>
                next_stop_name
                <input id=\"nextStopName\" placeholder=\"如 故宫\" />
              </label>
              <label>
                city_code
                <input id=\"cityCode\" placeholder=\"如 beijing\" />
              </label>
            </div>
            <div class=\"field-grid triple\">
              <label>
                plan_summary
                <input id=\"planSummary\" placeholder=\"如 经典中轴线一日游\" />
              </label>
              <label>
                stop_count
                <input id=\"stopCount\" type=\"number\" placeholder=\"可选\" />
              </label>
              <label>
                remaining_stop_count
                <input id=\"remainingStopCount\" type=\"number\" placeholder=\"可选\" />
              </label>
            </div>
            <div class=\"field-grid triple\">
              <label>
                current_stop_index
                <input id=\"currentStopIndex\" type=\"number\" placeholder=\"可选\" />
              </label>
              <label>
                itinerary_id
                <input id=\"itineraryId\" placeholder=\"可选\" />
              </label>
              <label>
                itinerary_version_id
                <input id=\"itineraryVersionId\" placeholder=\"可选\" />
              </label>
            </div>

            <h3 style=\"margin-top:20px;\">用户画像 / Prompt 变量覆盖</h3>
            <div class=\"field-grid triple\">
              <label>
                preferred_language
                <input id=\"preferredLanguage\" placeholder=\"如 zh\" />
              </label>
              <label>
                travel_style
                <select id=\"travelStyle\">
                  <option value=\"relaxed\">relaxed</option>
                  <option value=\"balanced\" selected>balanced</option>
                  <option value=\"efficient\">efficient</option>
                </select>
              </label>
              <label>
                walking_preference
                <select id=\"walkingPreference\">
                  <option value=\"low\">low</option>
                  <option value=\"medium\" selected>medium</option>
                  <option value=\"high\">high</option>
                </select>
              </label>
            </div>
            <div class=\"field-grid triple\">
              <label>
                pace_preference
                <select id=\"pacePreference\">
                  <option value=\"relaxed\">relaxed</option>
                  <option value=\"balanced\" selected>balanced</option>
                  <option value=\"fast\">fast</option>
                </select>
              </label>
              <label>
                audience_type
                <input id=\"audienceType\" placeholder=\"如 general\" />
              </label>
              <label>
                answer_length_preference
                <select id=\"answerLengthPreference\">
                  <option value=\"short\">short</option>
                  <option value=\"medium\" selected>medium</option>
                  <option value=\"long\">long</option>
                </select>
              </label>
            </div>
            <div class=\"field-grid\">
              <label>
                guide_style_preference
                <select id=\"guideStylePreference\">
                  <option value=\"NF\">NF</option>
                  <option value=\"NT\">NT</option>
                  <option value=\"SJ\" selected>SJ</option>
                  <option value=\"SP\">SP</option>
                </select>
              </label>
              <label>
                interests（逗号分隔）
                <input id=\"interests\" placeholder=\"如 history, architecture\" />
              </label>
            </div>

            <h3 style=\"margin-top:20px;\">景点上下文覆盖</h3>
            <div class=\"field-grid\">
              <label>
                attraction.name
                <input id=\"attractionName\" placeholder=\"如 故宫\" />
              </label>
              <label>
                attraction.category
                <input id=\"attractionCategory\" placeholder=\"如 museum\" />
              </label>
            </div>
            <div class=\"field-grid\">
              <label>
                attraction.highlights（逗号分隔）
                <input id=\"attractionHighlights\" placeholder=\"如 太和殿, 中轴线\" />
              </label>
              <label>
                attraction.visitor_tips（逗号分隔）
                <input id=\"attractionTips\" placeholder=\"如 建议预留 2 小时\" />
              </label>
            </div>
            <label>
              attraction.short_intro
              <textarea id=\"attractionIntro\" placeholder=\"如：故宫是明清两代皇家宫殿。\"></textarea>
            </label>
            <label>
              attraction.history
              <textarea id=\"attractionHistory\" placeholder=\"如：它集中体现了礼制与中轴线秩序。\"></textarea>
            </label>

            <h3 style=\"margin-top:20px;\">最近对话覆写</h3>
            <label>
              dialogue_history(JSON 数组)
              <textarea id=\"dialogueHistory\" class=\"mono\" placeholder='[{"role":"user","content":"我们今天想慢一点逛。"}]'></textarea>
            </label>

            <div class=\"actions\">
              <button class=\"primary\" id=\"askBtn\">发送 QA 请求</button>
              <button class=\"secondary\" id=\"previewBtn\">预览路由与 Prompt</button>
              <button class=\"ghost\" id=\"copyBtn\">复制请求 JSON</button>
            </div>
            <div class=\"status\" id=\"status\">准备就绪。</div>
            <ul class=\"hint-list\">
              <li>“发送 QA 请求”现在只走一次 <span class=\"mono\">/api/v1/qa/ask</span>；如果只看路由或 Prompt，请单独点“预览路由与 Prompt”。</li>
              <li>如果填写了真实 <span class=\"mono\">guide_session_id</span>，后端会先读取真实 session，再用这里显式填写的覆写字段叠加。</li>
              <li>默认只发最小请求；所有覆写都通过 <span class=\"mono\">context.qa_playground</span> 注入，便于定位是页面问题还是后端问题。</li>
            </ul>
          </div>
        </div>

        <div class=\"column\">
          <div class=\"card\">
            <div class=\"panel-title\">
              <div>
                <h2>回答结果</h2>
                <div class=\"subtle\">这里展示最终用户可见回答，以及意图、降级状态和关键信息。</div>
              </div>
            </div>
            <div class=\"badge-row\" id=\"metaBadges\"></div>
            <div class=\"answer-box\" id=\"answerBox\">尚未发送请求。</div>
            <div class=\"summary-grid\">
              <div class=\"summary-card\">
                <h3>链路摘要</h3>
                <div class=\"summary-list\" id=\"routeSummary\"></div>
              </div>
              <div class=\"summary-card\">
                <h3>耗时摘要</h3>
                <div class=\"summary-list\" id=\"latencySummary\"></div>
              </div>
            </div>
          </div>

          <div class=\"card\">
            <div class=\"tabs\">
              <button class=\"tab active\" data-tab=\"response\">完整响应</button>
              <button class=\"tab\" data-tab=\"preview\">预览结果</button>
              <button class=\"tab\" data-tab=\"prompt\">Prompt</button>
              <button class=\"tab\" data-tab=\"request\">请求 JSON</button>
            </div>
            <div class=\"result-box mono\" id=\"resultBox\">等待操作。</div>
          </div>
        </div>
      </div>
    </div>

    <script>
      const state = {
        response: null,
        preview: null,
        request: null,
        activeTab: 'response',
      };

      const els = {
        query: document.getElementById('query'),
        language: document.getElementById('language'),
        userId: document.getElementById('userId'),
        guideSessionId: document.getElementById('guideSessionId'),
        market: document.getElementById('market'),
        llmProvider: document.getElementById('llmProvider'),
        llmModel: document.getElementById('llmModel'),
        preset: document.getElementById('preset'),
        currentStopName: document.getElementById('currentStopName'),
        nextStopName: document.getElementById('nextStopName'),
        cityCode: document.getElementById('cityCode'),
        planSummary: document.getElementById('planSummary'),
        stopCount: document.getElementById('stopCount'),
        remainingStopCount: document.getElementById('remainingStopCount'),
        currentStopIndex: document.getElementById('currentStopIndex'),
        itineraryId: document.getElementById('itineraryId'),
        itineraryVersionId: document.getElementById('itineraryVersionId'),
        preferredLanguage: document.getElementById('preferredLanguage'),
        travelStyle: document.getElementById('travelStyle'),
        walkingPreference: document.getElementById('walkingPreference'),
        pacePreference: document.getElementById('pacePreference'),
        audienceType: document.getElementById('audienceType'),
        answerLengthPreference: document.getElementById('answerLengthPreference'),
        guideStylePreference: document.getElementById('guideStylePreference'),
        interests: document.getElementById('interests'),
        attractionName: document.getElementById('attractionName'),
        attractionCategory: document.getElementById('attractionCategory'),
        attractionHighlights: document.getElementById('attractionHighlights'),
        attractionTips: document.getElementById('attractionTips'),
        attractionIntro: document.getElementById('attractionIntro'),
        attractionHistory: document.getElementById('attractionHistory'),
        dialogueHistory: document.getElementById('dialogueHistory'),
        askBtn: document.getElementById('askBtn'),
        previewBtn: document.getElementById('previewBtn'),
        copyBtn: document.getElementById('copyBtn'),
        status: document.getElementById('status'),
        answerBox: document.getElementById('answerBox'),
        resultBox: document.getElementById('resultBox'),
        metaBadges: document.getElementById('metaBadges'),
        routeSummary: document.getElementById('routeSummary'),
        latencySummary: document.getElementById('latencySummary'),
        tabs: Array.from(document.querySelectorAll('.tab')),
      };

      const presets = {
        default: {
          query: '请简短介绍一下故宫。',
          language: 'zh',
        },
        trip: {
          query: '我现在到哪一站了？下一站是什么？',
          language: 'zh',
          currentStopName: '天安门广场',
          nextStopName: '故宫',
          cityCode: 'beijing',
        },
        translation: {
          query: 'Please translate: 请帮我拍张照片',
          language: 'en',
        },
        weather: {
          query: '今天适合去故宫吗，天气怎么样？',
          language: 'zh',
          attractionName: '故宫',
          cityCode: 'beijing',
        },
        navigation: {
          query: '从天安门到故宫再到景山怎么走？',
          language: 'zh',
          currentStopName: '天安门广场',
          nextStopName: '故宫',
          cityCode: 'beijing',
        },
      };

      function splitCsv(value) {
        return value
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean);
      }

      function parseOptionalInt(value) {
        const trimmed = String(value ?? '').trim();
        if (!trimmed) return null;
        const parsed = Number.parseInt(trimmed, 10);
        return Number.isFinite(parsed) ? parsed : null;
      }

      function parseDialogueHistory() {
        const raw = els.dialogueHistory.value.trim();
        if (!raw) return [];
        try {
          const parsed = JSON.parse(raw);
          return Array.isArray(parsed) ? parsed : [];
        } catch (error) {
          throw new Error('dialogue_history 不是合法 JSON 数组');
        }
      }

      function compactObject(value) {
        if (Array.isArray(value)) {
          const next = value
            .map((item) => compactObject(item))
            .filter((item) => item !== null && item !== undefined && (!Array.isArray(item) || item.length > 0));
          return next.length ? next : null;
        }
        if (value && typeof value === 'object') {
          const next = Object.fromEntries(
            Object.entries(value)
              .map(([key, inner]) => [key, compactObject(inner)])
              .filter(([, inner]) => inner !== null && inner !== undefined)
          );
          return Object.keys(next).length ? next : null;
        }
        if (typeof value === 'string') {
          const trimmed = value.trim();
          return trimmed ? trimmed : null;
        }
        return value ?? null;
      }

      function buildPayload() {
        const dialogueHistory = parseDialogueHistory();
        const sessionOverride = compactObject({
          guide_session_id: els.guideSessionId.value,
          itinerary_id: els.itineraryId.value,
          itinerary_version_id: els.itineraryVersionId.value,
          current_stop_name: els.currentStopName.value,
          next_stop_name: els.nextStopName.value,
          city_code: els.cityCode.value,
          plan_summary: els.planSummary.value,
          stop_count: parseOptionalInt(els.stopCount.value),
          remaining_stop_count: parseOptionalInt(els.remainingStopCount.value),
          current_stop_index: parseOptionalInt(els.currentStopIndex.value),
        });
        const profileOverride = compactObject({
          user_id: els.userId.value,
          preferred_language: els.preferredLanguage.value,
          interests: splitCsv(els.interests.value),
          travel_style: els.travelStyle.value,
          walking_preference: els.walkingPreference.value,
          pace_preference: els.pacePreference.value,
          audience_type: els.audienceType.value,
          answer_length_preference: els.answerLengthPreference.value,
          guide_style_preference: els.guideStylePreference.value,
        });
        const attractionOverride = compactObject({
          name: els.attractionName.value,
          category: els.attractionCategory.value,
          short_intro: els.attractionIntro.value,
          history: els.attractionHistory.value,
          highlights: splitCsv(els.attractionHighlights.value),
          visitor_tips: splitCsv(els.attractionTips.value),
        });
        const qaPlayground = compactObject({
          session_override: sessionOverride,
          profile_override: profileOverride,
          attraction_override: attractionOverride,
          dialogue_history: dialogueHistory,
        });
        const context = compactObject({
          market: els.market.value || 'beijing',
          user_id: els.userId.value,
          qa_playground: qaPlayground,
        }) || {};
        return {
          query: els.query.value.trim(),
          language: els.language.value.trim() || 'zh',
          user_id: els.userId.value.trim() || null,
          guide_session_id: els.guideSessionId.value.trim() || null,
          llm_provider: els.llmProvider.value.trim() || null,
          llm_model: els.llmModel.value.trim() || null,
          context,
        };
      }

      function setStatus(message, type = 'info') {
        els.status.textContent = message;
        els.status.style.color = type === 'error' ? '#b91c1c' : type === 'success' ? '#0f766e' : '#667085';
      }

      function setActiveTab(name) {
        state.activeTab = name;
        els.tabs.forEach((tab) => {
          tab.classList.toggle('active', tab.dataset.tab === name);
        });
        renderResult();
      }

      function renderSummaryList(el, items) {
        if (!items.length) {
          el.innerHTML = '<div class="summary-item"><span>状态</span><span>尚未生成</span></div>';
          return;
        }
        el.innerHTML = items
          .map((item) => `<div class="summary-item"><span>${item.label}</span><span>${item.value}</span></div>`)
          .join('');
      }

      function formatLatency(value) {
        return typeof value === 'number' ? `${value} ms` : '—';
      }

      function renderBadges() {
        const data = state.response?.data;
        const preview = state.preview?.data;
        const metadata = data?.metadata || {};
        const badges = [];
        if (data?.intent) badges.push(`intent: ${data.intent}`);
        if (data?.supported !== undefined) badges.push(`supported: ${String(data.supported)}`);
        if (metadata.degraded !== undefined) badges.push(`degraded: ${String(metadata.degraded)}`);
        if (metadata.llm?.provider) badges.push(`llm: ${metadata.llm.provider}/${metadata.llm.model}`);
        if (preview?.resolved_query?.used_translation_pivot || metadata.resolved_query?.used_translation_pivot) badges.push('pivot: true');
        if (metadata.playground?.enabled || state.request?.context?.qa_playground) badges.push('playground override: on');
        els.metaBadges.innerHTML = badges.map((item) => `<span class="badge">${item}</span>`).join('');
      }

      function renderAnswer() {
        const data = state.response?.data;
        const metadata = data?.metadata || {};
        const latency = metadata.latency_ms || {};
        const routeItems = [];
        const latencyItems = [];
        els.answerBox.textContent = data?.answer || '尚未发送请求。';

        if (data) {
          routeItems.push({ label: '最终 intent', value: data.intent || '—' });
          routeItems.push({ label: 'translation pivot', value: String(Boolean(metadata.resolved_query?.used_translation_pivot)) });
          routeItems.push({ label: 'router fallback', value: String(Boolean(metadata.intent_router?.fallback_result)) });
          routeItems.push({ label: 'answer translation', value: String(Boolean(metadata.answer_translation?.used_answer_translation)) });
          routeItems.push({ label: 'retrieval strategy', value: metadata.retrieval_strategy || metadata.rag_retrieval_mode || '—' });
          routeItems.push({ label: 'degraded reason', value: metadata.degraded_reason || '—' });
          routeItems.push({ label: 'LLM', value: metadata.llm?.provider ? `${metadata.llm.provider}/${metadata.llm.model}` : '—' });

          latencyItems.push({ label: 'preprocess', value: formatLatency(latency.preprocess_ms) });
          latencyItems.push({ label: 'routing', value: formatLatency(latency.routing_ms) });
          latencyItems.push({ label: 'context build', value: formatLatency(latency.context_build_ms) });
          latencyItems.push({ label: 'generation', value: formatLatency(latency.generation_ms) });
          latencyItems.push({ label: 'postprocess', value: formatLatency(latency.postprocess_ms) });
          latencyItems.push({ label: 'total', value: formatLatency(latency.total_ms) });
        }

        renderSummaryList(els.routeSummary, routeItems);
        renderSummaryList(els.latencySummary, latencyItems);
      }

      function renderResult() {
        if (state.activeTab === 'response') {
          els.resultBox.textContent = state.response ? JSON.stringify(state.response, null, 2) : '等待发送 QA 请求。';
          return;
        }
        if (state.activeTab === 'preview') {
          els.resultBox.textContent = state.preview ? JSON.stringify(state.preview, null, 2) : '等待预览。';
          return;
        }
        if (state.activeTab === 'prompt') {
          const prompt = state.preview?.data?.prompt_preview;
          els.resultBox.textContent = prompt ? JSON.stringify(prompt, null, 2) : '当前意图没有生成式 prompt，或尚未执行预览。';
          return;
        }
        els.resultBox.textContent = state.request ? JSON.stringify(state.request, null, 2) : '尚未生成请求。';
      }

      async function postJson(url, payload) {
        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data?.detail || `请求失败：${response.status}`);
        }
        return data;
      }

      async function runPreview() {
        const payload = buildPayload();
        state.request = payload;
        renderResult();
        setStatus('正在预览路由和 prompt…');
        const result = await postJson('/api/v1/qa/preview', payload);
        state.preview = result;
        renderBadges();
        renderResult();
        setStatus('预览完成。', 'success');
        return result;
      }

      async function runAsk() {
        const payload = buildPayload();
        state.request = payload;
        renderResult();
        setStatus('正在调用 QA 主链路…');
        const result = await postJson('/api/v1/qa/ask', payload);
        state.response = result;
        renderAnswer();
        renderBadges();
        renderResult();
        setStatus('QA 请求完成。', 'success');
        return result;
      }

      els.askBtn.addEventListener('click', async () => {
        try {
          await runAsk();
          setActiveTab('response');
        } catch (error) {
          setStatus(error.message || '请求失败。', 'error');
        }
      });

      els.previewBtn.addEventListener('click', async () => {
        try {
          await runPreview();
          setActiveTab('preview');
        } catch (error) {
          setStatus(error.message || '预览失败。', 'error');
        }
      });

      els.copyBtn.addEventListener('click', async () => {
        try {
          const payload = buildPayload();
          state.request = payload;
          renderResult();
          await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
          setStatus('请求 JSON 已复制。', 'success');
          setActiveTab('request');
        } catch (error) {
          setStatus(error.message || '复制失败。', 'error');
        }
      });

      els.tabs.forEach((tab) => {
        tab.addEventListener('click', () => setActiveTab(tab.dataset.tab));
      });

      function resetOverrideFields() {
        els.userId.value = '';
        els.guideSessionId.value = '';
        els.llmProvider.value = '';
        els.llmModel.value = '';
        els.currentStopName.value = '';
        els.nextStopName.value = '';
        els.cityCode.value = '';
        els.planSummary.value = '';
        els.stopCount.value = '';
        els.remainingStopCount.value = '';
        els.currentStopIndex.value = '';
        els.itineraryId.value = '';
        els.itineraryVersionId.value = '';
        els.preferredLanguage.value = '';
        els.travelStyle.value = 'balanced';
        els.walkingPreference.value = 'medium';
        els.pacePreference.value = 'balanced';
        els.audienceType.value = '';
        els.answerLengthPreference.value = 'medium';
        els.guideStylePreference.value = 'SJ';
        els.interests.value = '';
        els.attractionName.value = '';
        els.attractionCategory.value = '';
        els.attractionHighlights.value = '';
        els.attractionTips.value = '';
        els.attractionIntro.value = '';
        els.attractionHistory.value = '';
        els.dialogueHistory.value = '';
      }

      els.preset.addEventListener('change', () => {
        const preset = presets[els.preset.value];
        if (!preset) return;
        resetOverrideFields();
        if (preset.query) els.query.value = preset.query;
        if (preset.language) els.language.value = preset.language;
        if (preset.currentStopName) els.currentStopName.value = preset.currentStopName;
        if (preset.nextStopName) els.nextStopName.value = preset.nextStopName;
        if (preset.cityCode) els.cityCode.value = preset.cityCode;
        if (preset.attractionName) els.attractionName.value = preset.attractionName;
        state.request = buildPayload();
        renderBadges();
        renderAnswer();
        renderResult();
        setStatus('已切换场景。');
      });

      state.request = buildPayload();
      renderBadges();
      renderAnswer();
      renderResult();
    </script>
  </body>
</html>
"""
