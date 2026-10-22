import { Container } from "@/components/layout/container";
import { PaperWorkspace } from "@/features/research/paper-workspace";
export default async function Page({params}:{params:Promise<{paperId:string}>}){const {paperId}=await params; return <main id="main-content"><Container className="py-10"><PaperWorkspace paperId={paperId}/></Container></main>;}
