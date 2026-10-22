import { Container } from "@/components/layout/container";
import { ConversationsWorkspace } from "@/features/research/conversations-workspace";
import { ProfileGuard } from "@/features/profile/profile-guard";
export default function Page(){return <main id="main-content"><Container className="py-10"><ProfileGuard><h1 className="mb-6 text-3xl">Conversations</h1><ConversationsWorkspace/></ProfileGuard></Container></main>;}
