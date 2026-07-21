// TrueFrame.jsx
//
// Exports each selected artboard as a sanitized, validated layout SVG into this repo's layout/templates/<ratio>/<name>.svg.
// Fixes Illustrator's hex-escaped ids and Crop_Zones groups exported without their parent layer.
// SUPPORTED_RATIOS and the required rect/group ids are hand-duplicated from layout/mask.py and layout/crop.py since ExtendScript can't import Python.
//
// Install: see plugins/illustrator/README.md

(function () {
    if (app.documents.length === 0) {
        alert("TrueFrame: open a document with at least one artboard first.");
        return;
    }

    var doc = app.activeDocument;
    var SUPPORTED_RATIOS = ["1:1", "9:16", "16:9"]; // matches layout/mask.py's SUPPORTED_GENERATION_ASPECT_RATIOS
    var RATIO_ID_PATTERN = /^_?\d+:\d+(-\d+)?$/; // matches layout/crop.py's normalize_ratio() convention

    function ratioValue(label) {
        var parts = label.split(":");
        return Number(parts[0]) / Number(parts[1]);
    }

    function nearestSupportedRatio(width, height) {
        var target = width / height;
        var best = SUPPORTED_RATIOS[0];
        var bestDiff = Math.abs(ratioValue(best) - target);
        for (var i = 1; i < SUPPORTED_RATIOS.length; i++) {
            var diff = Math.abs(ratioValue(SUPPORTED_RATIOS[i]) - target);
            if (diff < bestDiff) {
                best = SUPPORTED_RATIOS[i];
                bestDiff = diff;
            }
        }
        return best;
    }

    function sanitizeName(raw) {
        var s = String(raw || "").toLowerCase();
        s = s.replace(/[^a-z0-9]+/g, "_");
        s = s.replace(/^_+|_+$/g, "");
        return s;
    }

    // Rewrites Illustrator's "_xHH_" hex-escaped id characters (e.g. "_x5F_" -> "_") back to plain text.
    function decodeIdEscapes(svgText) {
        return svgText.replace(/id="([^"]*)"/g, function (full, idVal) {
            var decoded = idVal.replace(/_x([0-9A-Fa-f]{1,6})_/g, function (m, hex) {
                return String.fromCharCode(parseInt(hex, 16));
            });
            return 'id="' + decoded + '"';
        });
    }

    var CANONICAL_ZONE_IDS = ["product", "header", "body", "spacer", "Product_Zones", "Copy_Zones", "Crop_Zones"];

    // Strips Illustrator's document-wide dedup suffix (a long numeric id, e.g. "product_0000045608712381742929620000008998566533944603012_") from every id, since a single-artboard export only ever has one real instance of a given zone.
    function stripDocumentWideDedupArtifacts(svgText) {
        return svgText.replace(/id="([^"]*)"/g, function (full, idVal) {
            return 'id="' + idVal.replace(/_\d{6,}_?$/, "") + '"';
        });
    }

    function canonicalizeZoneIds(svgText) {
        return svgText.replace(/id="([^"]*)"/g, function (full, idVal) {
            for (var i = 0; i < CANONICAL_ZONE_IDS.length; i++) {
                var canonical = CANONICAL_ZONE_IDS[i];
                var suffixPattern = new RegExp("^" + canonical + "(\\s+copy(\\s+\\d+)?|[\\s_-]+\\d+_?)$", "i");
                if (idVal === canonical || suffixPattern.test(idVal)) {
                    return 'id="' + canonical + '"';
                }
            }
            return full;
        });
    }

    // Walks <g>/</g> tags to record which ancestor <g> ids each id="..." is nested inside.
    function collectIdsWithAncestry(svgText) {
        var stack = [];
        var results = [];
        var tagRe = /<(\/?)([\w:-]+)((?:\s+[\w:-]+="[^"]*")*)\s*(\/?)>/g;
        var match;
        while ((match = tagRe.exec(svgText)) !== null) {
            var closing = match[1] === "/";
            var tagName = match[2];
            var attrs = match[3];
            var selfClosing = match[4] === "/";
            var idMatch = /\bid="([^"]*)"/.exec(attrs);
            var id = idMatch ? idMatch[1] : null;

            if (closing) {
                if (tagName === "g") stack.pop();
                continue;
            }
            if (id) {
                results.push({ id: id, ancestors: stack.slice() });
            }
            if (tagName === "g" && !selfClosing) {
                stack.push(id);
            }
        }
        return results;
    }

    function ancestorsInclude(ancestors, wanted) {
        for (var i = 0; i < ancestors.length; i++) {
            if (ancestors[i] === wanted) return true;
        }
        return false;
    }

    function anyEntryNestedIn(entries, wanted) {
        for (var i = 0; i < entries.length; i++) {
            if (ancestorsInclude(entries[i].ancestors, wanted)) return true;
        }
        return false;
    }

    // Throws on a hard failure (missing/misplaced "product" rect); otherwise returns non-fatal warning strings.
    function validateStructure(idsInfo) {
        var byId = {};
        for (var i = 0; i < idsInfo.length; i++) {
            var entry = idsInfo[i];
            if (!byId[entry.id]) byId[entry.id] = [];
            byId[entry.id].push(entry);
        }

        if (!byId["product"]) {
            throw new Error("no 'product' rect found - required for the placement mask and camera framing.");
        }
        if (!anyEntryNestedIn(byId["product"], "Product_Zones")) {
            throw new Error("'product' rect found, but not nested inside a 'Product_Zones' layer.");
        }

        var warnings = [];
        if (!byId["header"]) {
            warnings.push("no 'header' rect found (tagline copy zone)");
        } else if (!anyEntryNestedIn(byId["header"], "Copy_Zones")) {
            warnings.push("'header' rect found, but not nested inside a 'Copy_Zones' layer");
        }
        if (!byId["body"]) {
            warnings.push("no 'body' rect found (body copy zone)");
        } else if (!anyEntryNestedIn(byId["body"], "Copy_Zones")) {
            warnings.push("'body' rect found, but not nested inside a 'Copy_Zones' layer");
        }

        for (var id in byId) {
            if (!RATIO_ID_PATTERN.test(id)) continue;
            var entries = byId[id];
            var nested = false;
            for (var e = 0; e < entries.length; e++) {
                if (ancestorsInclude(entries[e].ancestors, "Crop_Zones")) {
                    nested = true;
                    break;
                }
            }
            if (!nested) {
                warnings.push("group '" + id + "' looks like a crop ratio but isn't nested inside a 'Crop_Zones' layer - it won't be picked up as a staged crop");
            }
        }

        return warnings;
    }

    function ensureFolder(path) {
        var f = new Folder(path);
        if (!f.exists) f.create();
        return f;
    }

    function writeFile(path, content) {
        var f = new File(path);
        f.encoding = "UTF-8";
        f.open("w");
        f.write(content);
        f.close();
    }

    // Exports exactly one artboard into a fresh temp folder, reads it back, then cleans up.
    function exportArtboardSVG(document, artboardIndex) {
        var tempFolder = new Folder(Folder.temp.fsName + "/trueframe_" + artboardIndex + "_" + Math.floor(Math.random() * 1e6));
        tempFolder.create();
        try {
            var tempFile = new File(tempFolder.fsName + "/export.svg");
            var opts = new ExportOptionsSVG();
            opts.saveMultipleArtboards = true;
            opts.artboardRange = String(artboardIndex + 1);
            opts.embedRasterImages = false;
            document.exportFile(tempFile, ExportType.SVG, opts);

            var produced = tempFolder.getFiles("*.svg");
            if (!produced || produced.length === 0) {
                throw new Error("Illustrator did not produce an SVG file for this artboard.");
            }
            var outputFile = produced[0];
            outputFile.encoding = "UTF-8";
            outputFile.open("r");
            var content = outputFile.read();
            outputFile.close();
            return content;
        } finally {
            var leftovers = tempFolder.getFiles();
            for (var i = 0; i < leftovers.length; i++) leftovers[i].remove();
            tempFolder.remove();
        }
    }

    function showSummary(results) {
        var lines = [];
        for (var i = 0; i < results.length; i++) {
            var r = results[i];
            var line = (r.status === "ok" ? "OK    " : "FAILED") + "  " + r.ratio + "/" + r.name;
            if (r.message) line += "\n         " + r.message;
            lines.push(line);
        }
        var resultsWin = new Window("dialog", "TrueFrame: Export Results");
        resultsWin.orientation = "column";
        resultsWin.alignChildren = "fill";
        resultsWin.margins = 16;
        var textBox = resultsWin.add("edittext", undefined, lines.join("\n"), { multiline: true, scrollable: true, readonly: true });
        textBox.preferredSize = [440, 260];
        var closeBtn = resultsWin.add("button", undefined, "Close", { name: "ok" });
        closeBtn.alignment = "right";
        closeBtn.onClick = function () { resultsWin.close(); };
        resultsWin.center();
        resultsWin.show();
    }

    // --- dialog ---
    var win = new Window("dialog", "TrueFrame");
    win.orientation = "column";
    win.alignChildren = "fill";
    win.spacing = 12;
    win.margins = 16;

    var header = win.add("statictext", undefined, "TrueFrame — export & validate layout SVGs from this document's artboards", { multiline: true });
    header.graphics.font = ScriptUI.newFont(header.graphics.font.name, "BOLD", 13);

    // --- one row per artboard: include + name + ratio ---
    var boardsPanel = win.add("panel", undefined, "Artboards");
    boardsPanel.orientation = "column";
    boardsPanel.alignChildren = "fill";
    boardsPanel.spacing = 6;
    boardsPanel.margins = 12;

    var artboardRows = [];
    for (var i = 0; i < doc.artboards.length; i++) {
        var ab = doc.artboards[i];
        var rect = ab.artboardRect; // [left, top, right, bottom]
        var width = Math.abs(rect[2] - rect[0]);
        var height = Math.abs(rect[1] - rect[3]);

        var row = boardsPanel.add("group");
        row.orientation = "row";
        row.alignChildren = "left";

        var includeCheckbox = row.add("checkbox", undefined, "");
        includeCheckbox.value = true;

        var nameField = row.add("edittext", undefined, sanitizeName(ab.name));
        nameField.preferredSize.width = 140;

        var ratioDropdown = row.add("dropdownlist", undefined, SUPPORTED_RATIOS);
        var nearest = nearestSupportedRatio(width, height);
        for (var r = 0; r < SUPPORTED_RATIOS.length; r++) {
            if (SUPPORTED_RATIOS[r] === nearest) {
                ratioDropdown.selection = r;
                break;
            }
        }

        artboardRows.push({
            artboardIndex: i,
            originalName: ab.name,
            includeCheckbox: includeCheckbox,
            nameField: nameField,
            ratioDropdown: ratioDropdown
        });
    }

    // --- layout/templates destination ---
    var templatesGroup = win.add("group");
    templatesGroup.orientation = "row";
    templatesGroup.alignChildren = "left";
    templatesGroup.add("statictext", undefined, "layout/templates folder:");
    var templatesField = templatesGroup.add("edittext", undefined, "");
    templatesField.preferredSize.width = 260;

    var scriptFile = new File($.fileName);
    var defaultTemplatesFolder = new Folder(scriptFile.path + "/../../layout/templates");
    if (defaultTemplatesFolder.exists) {
        templatesField.text = defaultTemplatesFolder.fsName;
    }

    var templatesBrowseButton = templatesGroup.add("button", undefined, "Browse...");
    templatesBrowseButton.onClick = function () {
        var folder = Folder.selectDialog("Select the repo's layout/templates folder");
        if (folder) templatesField.text = folder.fsName;
    };

    // --- actions ---
    var buttonGroup = win.add("group");
    buttonGroup.orientation = "row";
    buttonGroup.alignment = "right";
    var cancelButton = buttonGroup.add("button", undefined, "Cancel", { name: "cancel" });
    var exportButton = buttonGroup.add("button", undefined, "Export Layouts", { name: "ok" });

    cancelButton.onClick = function () {
        win.close();
    };

    exportButton.onClick = function () {
        if (!templatesField.text) {
            alert("TrueFrame: choose the layout/templates folder first.");
            return;
        }
        var templatesRoot = templatesField.text;
        var results = [];

        for (var i = 0; i < artboardRows.length; i++) {
            var row = artboardRows[i];
            if (!row.includeCheckbox.value) continue;

            var ratio = row.ratioDropdown.selection.text;
            var name = sanitizeName(row.nameField.text);

            if (!name) {
                results.push({ name: row.originalName, ratio: ratio, status: "error", message: "empty layout name" });
                continue;
            }

            try {
                var rawSvg = exportArtboardSVG(doc, row.artboardIndex);
                var decoded = decodeIdEscapes(rawSvg);
                decoded = stripDocumentWideDedupArtifacts(decoded);
                decoded = canonicalizeZoneIds(decoded);
                var idsInfo = collectIdsWithAncestry(decoded);
                var warnings = validateStructure(idsInfo);

                var ratioFolder = ensureFolder(templatesRoot + "/" + ratio.replace(":", "-"));
                var destPath = ratioFolder.fsName + "/" + name + ".svg";
                writeFile(destPath, decoded);

                results.push({ name: name, ratio: ratio, status: "ok", message: warnings.join("; ") });
            } catch (e) {
                // On a "no product rect" failure, surface the raw id="...product..." values to help diagnose an unrecognized Illustrator dedup format.
                var excerptMsg = "";
                if (typeof rawSvg !== "undefined") {
                    var idAttrRe = /id="([^"]*product[^"]*)"/gi;
                    var idMatches = [];
                    var idMatch;
                    while ((idMatch = idAttrRe.exec(rawSvg)) !== null) {
                        idMatches.push(idMatch[1]);
                    }
                    excerptMsg = idMatches.length ? " || raw id values: " + idMatches.join(" ~~~ ") : " || no id=\"...product...\" attribute found anywhere in raw export";
                }
                results.push({ name: name, ratio: ratio, status: "error", message: e.message + excerptMsg });
            }
        }

        win.close();
        showSummary(results);
    };

    win.center();
    win.show();
})();
