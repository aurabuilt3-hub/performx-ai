-- ====================================================================
-- PERFORMX Supabase Storage Migration: Private medical-documents bucket
-- Version: 20261011000001
-- ====================================================================

-- 1. Create the private 'medical-documents' storage bucket
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'medical-documents',
    'medical-documents',
    false, -- strictly private
    15728640, -- 15MB file size limit
    array['application/pdf', 'image/png', 'image/jpeg']
)
on conflict (id) do update set
    public = false,
    file_size_limit = 15728640,
    allowed_mime_types = array['application/pdf', 'image/png', 'image/jpeg'];

-- 2. Storage Objects RLS Policies for medical-documents bucket
-- Path pattern: users/{user_id}/documents/{document_id}.{ext}

create policy "Users can upload their own medical documents"
    on storage.objects for insert
    to authenticated
    with check (
        bucket_id = 'medical-documents' and
        (storage.foldername(name))[1] = 'users' and
        (storage.foldername(name))[2] = auth.uid()::text
    );

create policy "Users can read their own medical documents"
    on storage.objects for select
    to authenticated
    using (
        bucket_id = 'medical-documents' and
        (storage.foldername(name))[1] = 'users' and
        (storage.foldername(name))[2] = auth.uid()::text
    );

create policy "Users can delete their own medical documents"
    on storage.objects for delete
    to authenticated
    using (
        bucket_id = 'medical-documents' and
        (storage.foldername(name))[1] = 'users' and
        (storage.foldername(name))[2] = auth.uid()::text
    );
