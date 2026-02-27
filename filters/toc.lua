-- Lua filter: generates a static Table of Contents from headings.
-- Pandoc's built-in --toc creates a Word field that requires "Update Fields"
-- in Word/LibreOffice. This filter instead writes the TOC as visible text
-- so it appears immediately when the document is opened.

local headings = {}

-- First pass: collect all headings
function Header(el)
  table.insert(headings, { level = el.level, content = el.content, identifier = el.identifier })
  return nil  -- keep the heading as-is
end

-- Second pass: build the TOC and insert it at the start of the document
function Pandoc(doc)
  -- Collect headings from the document
  headings = {}
  doc:walk({ Header = Header })

  if #headings == 0 then
    return doc
  end

  -- Compute section numbers to match --number-sections output
  local counters = { 0, 0, 0 }
  local toc_items = {}
  for _, h in ipairs(headings) do
    -- Skip unnumbered headings (e.g. the TOC heading itself)
    local dominated_classes = h.classes or {}
    local dominated_attr = h.attr or {}
    local is_unnumbered = false
    if dominated_attr and dominated_attr.classes then
      for _, cls in ipairs(dominated_attr.classes) do
        if cls == "unnumbered" then is_unnumbered = true end
      end
    end

    if h.level <= 3 and not is_unnumbered then
      -- Increment counter at this level, reset deeper levels
      counters[h.level] = counters[h.level] + 1
      for i = h.level + 1, 3 do counters[i] = 0 end

      -- Build number string (e.g. "1", "1.1", "1.1.2")
      local num_parts = {}
      for i = 1, h.level do
        table.insert(num_parts, tostring(counters[i]))
      end
      local num_str = table.concat(num_parts, ".")

      local indent = ""
      if h.level == 2 then indent = "\u{00A0}\u{00A0}\u{00A0}\u{00A0}" end
      if h.level == 3 then indent = "\u{00A0}\u{00A0}\u{00A0}\u{00A0}\u{00A0}\u{00A0}\u{00A0}\u{00A0}" end

      local text = num_str .. "\u{00A0}\u{00A0}" .. pandoc.utils.stringify(h.content)
      local link = pandoc.Link(text, "#" .. h.identifier)
      table.insert(toc_items, pandoc.Plain({ pandoc.Str(indent), link }))
    end
  end

  local toc_header = pandoc.Header(1, "Table of Contents")
  toc_header.attr = pandoc.Attr("table-of-contents", {"unnumbered"}, {})

  local toc_block = { toc_header }
  for _, item in ipairs(toc_items) do
    table.insert(toc_block, item)
  end
  -- Page break after TOC (format-aware)
  table.insert(toc_block, pandoc.RawBlock("openxml", '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'))
  table.insert(toc_block, pandoc.RawBlock("latex", "\\newpage"))
  table.insert(toc_block, pandoc.RawBlock("html", '<div style="page-break-after: always;"></div>'))

  -- Insert TOC at the beginning (after any metadata title block)
  local new_blocks = {}
  local inserted = false
  for _, block in ipairs(doc.blocks) do
    if not inserted and block.t == "Header" then
      for _, tb in ipairs(toc_block) do
        table.insert(new_blocks, tb)
      end
      inserted = true
    end
    table.insert(new_blocks, block)
  end

  if not inserted then
    for _, tb in ipairs(toc_block) do
      table.insert(new_blocks, 1, tb)
    end
  end

  doc.blocks = new_blocks
  return doc
end
