// Shared types and constants for the app

export type ViewKey =
  | "dashboard"
  | "chat"
  | "tasks"
  | "karma"
  | "memory"
  | "review"
  | "settings";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export interface Task {
  id: number;
  title: string;
  sub_tasks: string[];
  execution_tips: string[];
  priority: string;
  discipline: string;
  completed: boolean;
}

export interface ChatMessage {
  role: "user" | "ai";
  content: string;
  bias_flag?: boolean;
  bias_description?: string;
  shadow_perspective?: string;
  ego_score?: number;
  ego_labels?: string[];
  memory_context?: string;
  tasks?: Task[];
}

export interface KarmaData {
  overview: {
    total_karma: number;
    average_daily_karma: number;
    current_streak_days: number;
    longest_streak_days: number;
    completion_rate: number;
    total_tasks_completed: number;
    total_tasks_attempted: number;
    days_tracked: number;
  };
  weekly_trends: any[];
  monthly_trends: any[];
  completion_heatmap: Record<string, number>;
  goal_areas: Record<string, number>;
}

export interface ProviderHealth {
  providers: Record<string, any>;
  report: string;
}