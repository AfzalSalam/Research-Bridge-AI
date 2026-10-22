import { z } from "zod";
import { parseApiData } from "./result";
import { paperDiscoveryResponseSchema, mentorDiscoveryResponseSchema } from "@/features/discovery/contracts";
export const paperSchema = paperDiscoveryResponseSchema.shape.papers.element;
export const candidateSchema = mentorDiscoveryResponseSchema.shape.candidates.element;
export const researchSchema = z.object({ id:z.string().uuid(), paper:paperSchema, collection:z.string(), note:z.string(), authorIds:z.array(z.string().uuid()), updatedAt:z.string() });
export const draftSummarySchema = z.object({id:z.string().uuid(),mentorId:z.string().nullable(),recipientDisplayName:z.string(),recipientContact:z.string().nullable(),subject:z.string(),draftVersion:z.number(),updatedAt:z.string()});
export type ResearchItem = z.infer<typeof researchSchema>;
export async function researchRequest<T>(path:string, schema:z.ZodType<T>, options:RequestInit = {}):Promise<T> {
 const {getAccessToken}=await import("./setup");
 const token = await getAccessToken();
 const response = await fetch(`/backend/api/v1${path}`,{...options,headers:{"Content-Type":"application/json",...(token ? {Authorization:`Bearer ${token}`} : {}),...options.headers}});
 const payload:unknown = response.status === 204 ? null : await response.json();
 return parseApiData({data:response.ok ? payload : undefined,error:response.ok ? undefined : payload,response},schema);
}
export const listResearch = () => researchRequest("/research/papers",z.array(researchSchema));
export const listDrafts = () => researchRequest("/research/drafts",z.array(draftSummarySchema));
export const saveResearch = (paperId:string, body:{collection?:string;note?:string;authorIds?:string[]}) => researchRequest(`/research/papers/${paperId}`,researchSchema,{method:"PUT",body:JSON.stringify(body)});
