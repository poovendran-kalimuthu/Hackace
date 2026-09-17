export type BlockType =
  | 'CHAPTER_TITLE'
  | 'HEADING_1'
  | 'HEADING_2'
  | 'HEADING_3'
  | 'BODY'
  | 'QUOTE'
  | 'CAPTION'
  | 'LIST'
  | 'TABLE'
  | 'IMAGE'
  | 'PAGE_BREAK'
  | 'UNKNOWN';

export interface Run {
  text: string;
  font_name?: string;
  font_size_pt?: number;
  bold: boolean;
  italic: boolean;
  underline: boolean;
  color?: string;
}

export interface Block {
  id: string;
  block_type: BlockType;
  text: string;
  runs: Run[];
  confidence: number;
  source_style: string;
  alignment: 'LEFT' | 'CENTER' | 'RIGHT' | 'JUSTIFY';
  left_indent_pt: number;
  right_indent_pt: number;
  space_before_pt: number;
  space_after_pt: number;
  line_spacing: number;
  is_page_break: boolean;
  metadata: Record<string, any>;
  user_corrected: boolean;
  predicted_type?: BlockType;
  original_index: number;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  source_filename: string;
  source_path: string;
  output_path: string;
  template_id: string;
  page_count: number;
  word_count: number;
  chapter_count: number;
  status: string;
  created_at: string;
  updated_at: string;
  root_dir: string;
}

export interface ElementStyle {
  font_family: string;
  font_size_pt: number;
  line_spacing: number;
  bold: boolean;
  italic: boolean;
  alignment: string;
  color: string;
  space_before_pt: number;
  space_after_pt: number;
  first_line_indent_pt: number;
  left_indent_pt: number;
  right_indent_pt: number;
  drop_cap?: boolean;
}

export interface TemplateComponent {
  id: string;
  name: string;
  component_type: string;
  x_percent: number;
  y_percent: number;
  width_percent: number;
  height_percent: number;
  style: ElementStyle;
  locked: boolean;
  visible: boolean;
  z_index: number;
  content_placeholder: string;
}

export interface PageTypeLayout {
  page_type: string;
  header_text: string;
  footer_text: string;
  show_header: boolean;
  show_footer: boolean;
  show_page_number: boolean;
  page_number_position: string;
  components: TemplateComponent[];
}

export interface BookTemplate {
  id: string;
  name: string;
  version: string;
  description: string;
  category: string;
  is_builtin: boolean;
  page: {
    width: number;
    height: number;
    unit: string;
    margin_top_in: number;
    margin_bottom_in: number;
    margin_inside_in: number;
    margin_outside_in: number;
    bleed_in: number;
  };
  styles: Record<string, ElementStyle>;
  page_types: Record<string, PageTypeLayout>;
}

export interface JobTelemetry {
  cpu_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  ram_percent: number;
  cpu_workers: number;
  io_workers: number;
}

export interface JobStatus {
  job_id: string;
  project_id: string;
  input_file: string;
  template_id: string;
  status: string;
  progress: number;
  current_stage: string;
  current_chunk: number;
  total_chunks: number;
  errors: string[];
  warnings: string[];
  output_file: string;
  telemetry?: JobTelemetry;
}

export interface ReviewItem {
  block_id: string;
  original_index: number;
  block_type: string;
  text_preview: string;
  full_text: string;
  confidence: number;
  estimated_page: number;
}
