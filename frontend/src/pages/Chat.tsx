import ChatInterface from '@/components/ChatInterface';

export default function Chat() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">AI Chat</h1>
        <p className="text-muted-foreground">
          Interact with an AI assistant powered by OpenAI.
        </p>
      </div>
      <ChatInterface />
    </div>
  );
}