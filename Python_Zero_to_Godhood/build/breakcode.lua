-- Pandoc Lua filter (LaTeX output only): let long inline code spans break.
--
-- pandoc renders inline code as \texttt{...}, which TeX treats as one
-- unbreakable word. Long dotted names, paths, and call expressions in prose
-- then overflow into the margin. This filter splits such spans at natural
-- punctuation boundaries and inserts \allowbreak, so a line may break after
-- a dot, slash, comma, bracket, or operator without any hyphen being added.
-- Short spans are left alone so ordinary identifiers never break.

local MIN_LEN = 14
local BREAK_AFTER = "[%.%/%,%(%[%]%=%:%-%+%*%|]"

function Code(el)
  if not FORMAT:match("latex") then return nil end
  local text = el.text
  if #text < MIN_LEN then return nil end
  local pieces = {}
  local start = 1
  local i = 1
  while i <= #text do
    local ch = text:sub(i, i)
    if ch:match(BREAK_AFTER) and i < #text then
      -- do not break inside a run of the same operator (e.g. "...", "==")
      local nxt = text:sub(i + 1, i + 1)
      if nxt ~= ch then
        table.insert(pieces, text:sub(start, i))
        start = i + 1
      end
    end
    i = i + 1
  end
  if start <= #text then table.insert(pieces, text:sub(start)) end
  if #pieces < 2 then return nil end
  local out = {}
  for k, p in ipairs(pieces) do
    if k > 1 then table.insert(out, pandoc.RawInline("latex", "\\allowbreak{}")) end
    local c = pandoc.Code(p)
    c.attr = el.attr
    table.insert(out, c)
  end
  return out
end

-- A slash joining words or code spans in prose ("a/b/c", `x`/`y`) is also an
-- unbreakable compound; permit a break after each slash.
function Str(el)
  if not FORMAT:match("latex") then return nil end
  local text = el.text
  if not text:find("/", 1, true) then return nil end
  local out = {}
  for piece, slash in text:gmatch("([^/]*)(/?)") do
    if piece ~= "" then table.insert(out, pandoc.Str(piece)) end
    if slash ~= "" then
      table.insert(out, pandoc.Str("/"))
      table.insert(out, pandoc.RawInline("latex", "\\allowbreak{}"))
    end
  end
  return out
end

-- Tables written as pipe tables with short source lines get no column widths
-- from pandoc, so LaTeX sets them with `l` columns that cannot wrap; a cell
-- holding a long code span then runs into the margin. Give every such table
-- proportional widths (by the longest cell in each column) so pandoc emits
-- wrapping p{} columns instead.
local function cell_len(cell)
  return #pandoc.utils.stringify(cell)
end

-- Narrowest width (as a fraction of the text width) a cell can take without
-- an overfull line: its longest unbreakable token. Code tokens are measured at
-- the monospace width, prose tokens at the narrower body-face width.
local CHAR_MONO = 0.0150   -- JetBrains Mono, Scale=0.86 of 10.95pt, 386pt measure
local CHAR_PROSE = 0.0125  -- Charter average advance, same measure
local PAD_FRAC = 0.035     -- longtable cell padding
local TOTAL = 0.98

local function cell_need(cell)
  local need = 0
  pandoc.walk_block(pandoc.Div(cell.content), {
    Code = function(el)
      for tok in el.text:gmatch("%S+") do
        need = math.max(need, #tok * CHAR_MONO)
      end
    end,
    Str = function(el)
      need = math.max(need, #el.text * CHAR_PROSE)
    end,
  })
  return need + PAD_FRAC
end

function Table(tbl)
  if not FORMAT:match("latex") then return nil end
  local ncols = #tbl.colspecs
  local presized = false
  for _, spec in ipairs(tbl.colspecs) do
    if spec[2] ~= nil and spec[2] ~= "ColWidthDefault" then presized = true end
  end
  local maxlen, need = {}, {}
  for c = 1, ncols do maxlen[c] = 4; need[c] = PAD_FRAC end
  local function scan(rows)
    for _, row in ipairs(rows) do
      for c, cell in ipairs(row.cells) do
        maxlen[c] = math.max(maxlen[c] or 4, cell_len(cell))
        need[c] = math.max(need[c] or PAD_FRAC, cell_need(cell))
      end
    end
  end
  scan(tbl.head.rows)
  for _, body in ipairs(tbl.bodies) do scan(body.body) end
  local total_text = 0
  for c = 1, ncols do total_text = total_text + maxlen[c] end
  -- Narrow tables set fine with `l` columns; leave them alone.
  if not presized and total_text <= 60 then return nil end
  -- Start from pandoc's own widths when it assigned them, otherwise from
  -- shares proportional to content; then raise any column that could not
  -- hold its longest token and take the difference from the rest.
  local share, wsum, need_sum = {}, 0, 0
  for c = 1, ncols do
    local w = tbl.colspecs[c][2]
    if presized and type(w) == "number" then share[c] = w
    else share[c] = math.min(maxlen[c], 60) ^ 0.8 end
    wsum = wsum + share[c]
    need_sum = need_sum + need[c]
  end
  for c = 1, ncols do share[c] = TOTAL * share[c] / wsum end
  -- If even the minimums do not fit, scale them to the measure: the table is
  -- simply too wide for the page and the least-bad result is a uniform squeeze.
  if need_sum > TOTAL then
    for c = 1, ncols do tbl.colspecs[c] = { tbl.colspecs[c][1], TOTAL * need[c] / need_sum } end
    return tbl
  end
  -- Pin columns that fall below their minimum, redistribute the rest, and
  -- repeat: redistribution can push another column below its minimum.
  local fixed = {}
  for _ = 1, ncols do
    local fixed_sum, free_sum, changed = 0, 0, false
    for c = 1, ncols do
      if not fixed[c] and share[c] < need[c] then fixed[c] = true; changed = true end
      if fixed[c] then fixed_sum = fixed_sum + need[c] else free_sum = free_sum + share[c] end
    end
    local remaining = TOTAL - fixed_sum
    for c = 1, ncols do
      if fixed[c] then share[c] = need[c]
      elseif remaining > 0 and free_sum > 0 then share[c] = share[c] * remaining / free_sum
      else share[c] = need[c] end
    end
    if not changed then break end
  end
  for c = 1, ncols do tbl.colspecs[c] = { tbl.colspecs[c][1], share[c] } end
  return tbl
end

-- pandoc wraps every line of a highlighted block in \NormalTok{...}. fvextra
-- cannot break inside a macro argument, so a single token wider than the
-- measure (a JSON document, a bytes literal) overflows. Unhighlighted blocks
-- (no language, or `text`) gain nothing from the wrapper: emit them as bare
-- Verbatim lines in the same Shaded box, where breakanywhere applies.
local function verbatim_escape(s)
  -- commandchars=\\\{\} : only backslash and braces are special
  s = s:gsub("\\", "\1")
  s = s:gsub("{", "\\{"):gsub("}", "\\}")
  s = s:gsub("\1", "\\textbackslash{}")
  return s
end

function CodeBlock(el)
  if not FORMAT:match("latex") then return nil end
  local lang = el.classes[1]
  if lang ~= nil and lang ~= "text" then return nil end
  local lines = {}
  for line in (el.text .. "\n"):gmatch("(.-)\n") do
    table.insert(lines, verbatim_escape(line))
  end
  return pandoc.RawBlock("latex",
    "\\begin{Shaded}\n\\begin{Highlighting}[]\n" ..
    table.concat(lines, "\n") .. "\n\\end{Highlighting}\n\\end{Shaded}")
end
