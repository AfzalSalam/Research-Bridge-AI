import { Container } from "@/components/layout/container";
import { RestoredDraft } from "@/features/research/restored-draft";
import { ProfileGuard } from "@/features/profile/profile-guard";
export default async function Page({params}:{params:Promise<{draftId:string}>}){const {draftId}=await params;return <main id="main-content"><Container className="py-10"><ProfileGuard><RestoredDraft draftId={draftId}/></ProfileGuard></Container></main>;}
