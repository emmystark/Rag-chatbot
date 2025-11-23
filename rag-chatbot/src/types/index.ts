export type Message = {
    id: string;
    role: "user" | "assistant";
    content: string;
    sources?: Source[];
  };
  
  export type Source = {
    text: string;
    source: string;
    page?: number;
  };