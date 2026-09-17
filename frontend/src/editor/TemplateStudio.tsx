import React, { useState } from 'react';
import {
  Type,
  Heading,
  Image as ImageIcon,
  Table as TableIcon,
  Quote,
  Hash,
  Minus,
  Save,
  Copy,
  Download,
  Upload,
  Lock,
  Unlock,
  Eye,
  EyeOff,
  Trash2,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Layers,
  Sliders,
  AlignLeft,
  AlignCenter,
  AlignRight,
  AlignJustify,
  Bold,
  Italic,
  BookOpen
} from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { BookTemplate, TemplateComponent } from '../types';
import { api } from '../services/api';

export const TemplateStudio: React.FC = () => {
  const { templates, activeTemplate, selectTemplate, loadTemplates } = useAppStore();
  const [selectedPageType, setSelectedPageType] = useState<string>('Normal Page');
  const [selectedComponentId, setSelectedComponentId] = useState<string | null>(null);
  const [zoom, setZoom] = useState<number>(100);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  // Fallback template if none selected
  const currentTemplate: BookTemplate = activeTemplate || templates[0] || {
    id: 'classic_novel',
    name: 'Classic Novel',
    version: '1.0',
    description: 'Traditional literary formatting',
    category: 'Novel',
    is_builtin: true,
    page: {
      width: 5.5,
      height: 8.5,
      unit: 'inch',
      margin_top_in: 0.8,
      margin_bottom_in: 0.8,
      margin_inside_in: 0.9,
      margin_outside_in: 0.7,
      bleed_in: 0.125,
    },
    styles: {
      body: {
        font_family: 'Garamond',
        font_size_pt: 11.0,
        line_spacing: 1.2,
        bold: false,
        italic: false,
        alignment: 'JUSTIFY',
        color: '#111827',
        space_before_pt: 0,
        space_after_pt: 0,
        first_line_indent_pt: 18,
        left_indent_pt: 0,
        right_indent_pt: 0,
      },
    },
    page_types: {},
  };

  const pageTypes = [
    'Cover',
    'Title Page',
    'Copyright Page',
    'Dedication',
    'Table of Contents',
    'Chapter Opening',
    'Normal Page',
    'Quote Page',
    'Image Page',
    'Table Page',
    'Appendix',
    'Back Matter',
  ];

  const toolboxComponents = [
    { type: 'CHAPTER_TITLE', label: 'Chapter Title', icon: Heading },
    { type: 'HEADING', label: 'Section Heading', icon: Heading },
    { type: 'TEXT', label: 'Body Text Box', icon: Type },
    { type: 'QUOTE', label: 'Blockquote', icon: Quote },
    { type: 'IMAGE', label: 'Image Placeholder', icon: ImageIcon },
    { type: 'TABLE', label: 'Table Grid', icon: TableIcon },
    { type: 'PAGE_NUMBER', label: 'Page Number', icon: Hash },
    { type: 'DIVIDER', label: 'Divider Ornament', icon: Minus },
  ];

  // Components on the currently active page type
  const activeLayout = currentTemplate.page_types[selectedPageType] || {
    page_type: selectedPageType,
    header_text: '',
    footer_text: '',
    show_header: true,
    show_footer: true,
    show_page_number: true,
    page_number_position: 'bottom-center',
    components: [],
  };

  const components = activeLayout.components || [];
  const selectedComponent = components.find((c) => c.id === selectedComponentId);

  const addComponent = (type: string, label: string) => {
    const newComp: TemplateComponent = {
      id: `comp_${Date.now()}`,
      name: `${label} ${components.length + 1}`,
      component_type: type,
      x_percent: 10,
      y_percent: Math.min(80, 15 + components.length * 12),
      width_percent: 80,
      height_percent: type === 'CHAPTER_TITLE' ? 14 : type === 'DIVIDER' ? 3 : 10,
      style: {
        font_family: currentTemplate.styles.body?.font_family || 'Garamond',
        font_size_pt: type === 'CHAPTER_TITLE' ? 24 : type === 'HEADING' ? 16 : 11,
        line_spacing: 1.2,
        bold: type === 'CHAPTER_TITLE' || type === 'HEADING',
        italic: type === 'QUOTE',
        alignment: type === 'CHAPTER_TITLE' || type === 'PAGE_NUMBER' ? 'CENTER' : 'JUSTIFY',
        color: '#111827',
        space_before_pt: 0,
        space_after_pt: 0,
        first_line_indent_pt: type === 'TEXT' ? 18 : 0,
        left_indent_pt: type === 'QUOTE' ? 24 : 0,
        right_indent_pt: type === 'QUOTE' ? 24 : 0,
      },
      locked: false,
      visible: true,
      z_index: components.length + 1,
      content_placeholder:
        type === 'CHAPTER_TITLE'
          ? 'Chapter One: The Awakening'
          : type === 'HEADING'
          ? '1.1 Theoretical Framework'
          : type === 'QUOTE'
          ? '“To be yourself in a world that is constantly trying to make you something else is the greatest accomplishment.”'
          : type === 'PAGE_NUMBER'
          ? '— {PAGE} —'
          : 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.',
    };

    const updatedLayout = {
      ...activeLayout,
      components: [...components, newComp],
    };

    const updatedTemplate = {
      ...currentTemplate,
      page_types: {
        ...currentTemplate.page_types,
        [selectedPageType]: updatedLayout,
      },
    };

    selectTemplate(updatedTemplate);
    setSelectedComponentId(newComp.id);
  };

  const updateSelectedComponent = (patch: Partial<TemplateComponent>) => {
    if (!selectedComponentId) return;

    const updatedComponents = components.map((c) =>
      c.id === selectedComponentId ? { ...c, ...patch } : c
    );

    const updatedTemplate = {
      ...currentTemplate,
      page_types: {
        ...currentTemplate.page_types,
        [selectedPageType]: {
          ...activeLayout,
          components: updatedComponents,
        },
      },
    };

    selectTemplate(updatedTemplate);
  };

  const updateSelectedStyle = (patch: Partial<TemplateComponent['style']>) => {
    if (!selectedComponent) return;
    updateSelectedComponent({
      style: { ...selectedComponent.style, ...patch },
    });
  };

  const deleteComponent = (id: string) => {
    const updatedComponents = components.filter((c) => c.id !== id);
    const updatedTemplate = {
      ...currentTemplate,
      page_types: {
        ...currentTemplate.page_types,
        [selectedPageType]: {
          ...activeLayout,
          components: updatedComponents,
        },
      },
    };
    selectTemplate(updatedTemplate);
    if (selectedComponentId === id) {
      setSelectedComponentId(null);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await api.saveTemplate(currentTemplate);
      await loadTemplates();
      alert('Template saved successfully.');
    } catch (err) {
      alert('Failed to save template.');
    } finally {
      setIsSaving(false);
    }
  };

  // Dimensions of canvas representation (based on page aspect ratio)
  const canvasWidthPx = 420 * (zoom / 100);
  const aspectRatio = currentTemplate.page.height / currentTemplate.page.width;
  const canvasHeightPx = canvasWidthPx * aspectRatio;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-slate-950 select-none">
      {/* Top Studio Toolbar */}
      <div className="h-12 glass-panel border-b border-slate-800/80 px-4 flex items-center justify-between text-xs z-20">
        <div className="flex items-center space-x-3">
          <span className="font-semibold text-white flex items-center space-x-1.5">
            <BookOpen className="w-4 h-4 text-sky-400" />
            <span>Template Studio:</span>
          </span>

          <select
            value={currentTemplate.id}
            onChange={(e) => {
              const tpl = templates.find((t) => t.id === e.target.value);
              if (tpl) selectTemplate(tpl);
            }}
            className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 text-xs focus:outline-none"
          >
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.page.width}" × {t.page.height}")
              </option>
            ))}
          </select>

          <span className="text-slate-500">•</span>
          <span className="text-slate-400">
            Trim: <span className="text-slate-200 font-mono">{currentTemplate.page.width}" × {currentTemplate.page.height}"</span>
          </span>
        </div>

        {/* Zoom & Save Actions */}
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1 bg-slate-900 border border-slate-800 rounded-lg p-0.5">
            <button
              onClick={() => setZoom((z) => Math.max(50, z - 10))}
              className="p-1 text-slate-400 hover:text-slate-200"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono text-[10px] text-slate-300 px-1">{zoom}%</span>
            <button
              onClick={() => setZoom((z) => Math.min(150, z + 10))}
              className="p-1 text-slate-400 hover:text-slate-200"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-white font-medium shadow-sm transition"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{isSaving ? 'Saving...' : 'Save Template'}</span>
          </button>
        </div>
      </div>

      {/* Main 3-Panel Work Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel: Components Toolbox & Layers */}
        <div className="w-64 glass-panel border-r border-slate-800/80 flex flex-col justify-between overflow-y-auto z-10">
          <div className="p-4 space-y-4">
            <div>
              <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center space-x-1.5">
                <Sliders className="w-3.5 h-3.5 text-sky-400" />
                <span>Components Toolbox</span>
              </h4>
              <p className="text-[11px] text-slate-500 mb-3">
                Click to add reusable elements to the {selectedPageType} canvas.
              </p>

              <div className="grid grid-cols-1 gap-1.5">
                {toolboxComponents.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.type}
                      onClick={() => addComponent(item.type, item.label)}
                      className="flex items-center space-x-2.5 px-3 py-2 rounded-xl bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800/60 hover:border-sky-500/40 text-slate-200 text-xs transition text-left group"
                    >
                      <Icon className="w-4 h-4 text-slate-400 group-hover:text-sky-400 transition" />
                      <span className="font-medium">{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Layer Tree */}
            <div className="pt-3 border-t border-slate-800/80">
              <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center space-x-1.5">
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                <span>Layers ({components.length})</span>
              </h4>

              {components.length === 0 ? (
                <p className="text-[11px] text-slate-600 italic">No components on this page type.</p>
              ) : (
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {components.map((comp) => (
                    <div
                      key={comp.id}
                      onClick={() => setSelectedComponentId(comp.id)}
                      className={`flex items-center justify-between p-2 rounded-lg text-xs cursor-pointer border transition ${
                        selectedComponentId === comp.id
                          ? 'bg-sky-500/15 border-sky-500/30 text-sky-300'
                          : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:bg-slate-800'
                      }`}
                    >
                      <span className="truncate max-w-[120px] font-medium">{comp.name}</span>
                      <div className="flex items-center space-x-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteComponent(comp.id);
                          }}
                          className="p-1 text-slate-500 hover:text-rose-400"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Center Panel: Interactive Page Canvas */}
        <div className="flex-1 bg-slate-950 flex flex-col items-center justify-center p-6 overflow-auto canvas-grid relative">
          {/* Visual Book Page */}
          <div
            style={{
              width: `${canvasWidthPx}px`,
              height: `${canvasHeightPx}px`,
            }}
            className="bg-white text-slate-900 rounded-sm shadow-2xl relative border border-slate-200 transition-all duration-150 overflow-hidden flex flex-col justify-between"
          >
            {/* Margin Guides */}
            <div
              style={{
                top: `${(currentTemplate.page.margin_top_in / currentTemplate.page.height) * 100}%`,
                bottom: `${(currentTemplate.page.margin_bottom_in / currentTemplate.page.height) * 100}%`,
                left: `${(currentTemplate.page.margin_inside_in / currentTemplate.page.width) * 100}%`,
                right: `${(currentTemplate.page.margin_outside_in / currentTemplate.page.width) * 100}%`,
              }}
              className="absolute border border-dashed border-sky-300/40 pointer-events-none z-0"
            />

            {/* Render Canvas Components */}
            {components.map((comp) => {
              const isSelected = selectedComponentId === comp.id;
              return (
                <div
                  key={comp.id}
                  onClick={() => setSelectedComponentId(comp.id)}
                  style={{
                    position: 'absolute',
                    top: `${comp.y_percent}%`,
                    left: `${comp.x_percent}%`,
                    width: `${comp.width_percent}%`,
                    fontFamily: comp.style.font_family,
                    fontSize: `${Math.max(8, comp.style.font_size_pt * (zoom / 100))}px`,
                    fontWeight: comp.style.bold ? 'bold' : 'normal',
                    fontStyle: comp.style.italic ? 'italic' : 'normal',
                    textAlign: comp.style.alignment.toLowerCase() as any,
                    color: comp.style.color,
                    lineHeight: comp.style.line_spacing,
                  }}
                  className={`cursor-pointer p-1.5 transition-all ${
                    isSelected
                      ? 'ring-2 ring-sky-500 bg-sky-500/10 rounded-sm'
                      : 'hover:ring-1 hover:ring-slate-300 rounded-sm'
                  }`}
                >
                  {comp.component_type === 'DIVIDER' ? (
                    <div className="w-full h-px bg-slate-400 my-2" />
                  ) : comp.component_type === 'IMAGE' ? (
                    <div className="w-full h-24 bg-slate-100 border border-dashed border-slate-300 rounded flex flex-col items-center justify-center text-slate-400">
                      <ImageIcon className="w-6 h-6 mb-1" />
                      <span className="text-[10px]">Image Placeholder</span>
                    </div>
                  ) : comp.component_type === 'TABLE' ? (
                    <div className="w-full border border-slate-300 text-[10px]">
                      <div className="grid grid-cols-3 bg-slate-100 font-bold p-1 border-b border-slate-300">
                        <span>Col A</span>
                        <span>Col B</span>
                        <span>Col C</span>
                      </div>
                      <div className="grid grid-cols-3 p-1">
                        <span>Val 1</span>
                        <span>Val 2</span>
                        <span>Val 3</span>
                      </div>
                    </div>
                  ) : (
                    <span>{comp.content_placeholder}</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Panel: Property Inspector */}
        <div className="w-72 glass-panel border-l border-slate-800/80 p-4 overflow-y-auto z-10 space-y-5">
          <div>
            <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1 flex items-center space-x-1.5">
              <Sliders className="w-3.5 h-3.5 text-sky-400" />
              <span>Properties Inspector</span>
            </h4>
            <p className="text-[10px] text-slate-500">
              {selectedComponent ? `Editing: ${selectedComponent.name}` : 'Select an element on the canvas to configure.'}
            </p>
          </div>

          {selectedComponent ? (
            <div className="space-y-4 text-xs">
              {/* Placement & Geometry */}
              <div className="space-y-2">
                <span className="font-semibold text-slate-300 block text-[11px]">Position & Geometry</span>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-slate-400">Y Offset (%)</label>
                    <input
                      type="number"
                      value={Math.round(selectedComponent.y_percent)}
                      onChange={(e) => updateSelectedComponent({ y_percent: Number(e.target.value) })}
                      className="w-full px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-200 text-xs mt-0.5"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Width (%)</label>
                    <input
                      type="number"
                      value={Math.round(selectedComponent.width_percent)}
                      onChange={(e) => updateSelectedComponent({ width_percent: Number(e.target.value) })}
                      className="w-full px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-200 text-xs mt-0.5"
                    />
                  </div>
                </div>
              </div>

              {/* Typography */}
              <div className="space-y-2 pt-2 border-t border-slate-800">
                <span className="font-semibold text-slate-300 block text-[11px]">Typography</span>

                <div>
                  <label className="text-[10px] text-slate-400">Font Family</label>
                  <select
                    value={selectedComponent.style.font_family}
                    onChange={(e) => updateSelectedStyle({ font_family: e.target.value })}
                    className="w-full px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-200 text-xs mt-0.5 font-serif"
                  >
                    <option value="Garamond">Garamond (Classic Serif)</option>
                    <option value="Georgia">Georgia (Modern Serif)</option>
                    <option value="Times New Roman">Times New Roman (Academic)</option>
                    <option value="Baskerville">Baskerville (Minimalist)</option>
                    <option value="Calibri">Calibri (Technical Sans)</option>
                    <option value="Arial">Arial (Clean Sans)</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-slate-400">Font Size (pt)</label>
                    <input
                      type="number"
                      value={selectedComponent.style.font_size_pt}
                      onChange={(e) => updateSelectedStyle({ font_size_pt: Number(e.target.value) })}
                      className="w-full px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-200 text-xs mt-0.5"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Line Spacing</label>
                    <input
                      type="number"
                      step="0.05"
                      value={selectedComponent.style.line_spacing}
                      onChange={(e) => updateSelectedStyle({ line_spacing: Number(e.target.value) })}
                      className="w-full px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-200 text-xs mt-0.5"
                    />
                  </div>
                </div>

                {/* Styling Toggles */}
                <div className="flex items-center space-x-1 pt-1">
                  <button
                    onClick={() => updateSelectedStyle({ bold: !selectedComponent.style.bold })}
                    className={`p-1.5 rounded ${
                      selectedComponent.style.bold ? 'bg-sky-500 text-white' : 'bg-slate-900 text-slate-400'
                    }`}
                  >
                    <Bold className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => updateSelectedStyle({ italic: !selectedComponent.style.italic })}
                    className={`p-1.5 rounded ${
                      selectedComponent.style.italic ? 'bg-sky-500 text-white' : 'bg-slate-900 text-slate-400'
                    }`}
                  >
                    <Italic className="w-3.5 h-3.5" />
                  </button>

                  <div className="h-4 w-px bg-slate-800 mx-1" />

                  {['LEFT', 'CENTER', 'RIGHT', 'JUSTIFY'].map((align) => (
                    <button
                      key={align}
                      onClick={() => updateSelectedStyle({ alignment: align })}
                      className={`p-1.5 rounded ${
                        selectedComponent.style.alignment === align ? 'bg-sky-500 text-white' : 'bg-slate-900 text-slate-400'
                      }`}
                    >
                      {align === 'LEFT' && <AlignLeft className="w-3.5 h-3.5" />}
                      {align === 'CENTER' && <AlignCenter className="w-3.5 h-3.5" />}
                      {align === 'RIGHT' && <AlignRight className="w-3.5 h-3.5" />}
                      {align === 'JUSTIFY' && <AlignJustify className="w-3.5 h-3.5" />}
                    </button>
                  ))}
                </div>
              </div>

              {/* Spacing & Indentation */}
              <div className="space-y-2 pt-2 border-t border-slate-800">
                <span className="font-semibold text-slate-300 block text-[11px]">Margins & Indent</span>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-slate-400">Space Before (pt)</label>
                    <input
                      type="number"
                      value={selectedComponent.style.space_before_pt}
                      onChange={(e) => updateSelectedStyle({ space_before_pt: Number(e.target.value) })}
                      className="w-full px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-200 text-xs mt-0.5"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">First-Line Indent (pt)</label>
                    <input
                      type="number"
                      value={selectedComponent.style.first_line_indent_pt}
                      onChange={(e) => updateSelectedStyle({ first_line_indent_pt: Number(e.target.value) })}
                      className="w-full px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-200 text-xs mt-0.5"
                    />
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500 text-xs">
              <p>No element selected.</p>
              <p className="mt-1 text-[11px] text-slate-600">
                Click any element on the page canvas or select a layer to inspect its styling.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Bar: Reusable Page Types Selector */}
      <div className="h-12 glass-panel border-t border-slate-800/80 px-4 flex items-center space-x-2 overflow-x-auto z-20">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-2 flex-shrink-0">
          Page Types:
        </span>
        <div className="flex items-center space-x-1.5">
          {pageTypes.map((pt) => {
            const isSel = selectedPageType === pt;
            return (
              <button
                key={pt}
                onClick={() => {
                  setSelectedPageType(pt);
                  setSelectedComponentId(null);
                }}
                className={`px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                  isSel
                    ? 'bg-sky-500/20 text-sky-400 border border-sky-500/40 font-semibold'
                    : 'bg-slate-900/60 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {pt}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
