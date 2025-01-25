import { NextRequest, NextResponse } from 'next/server';
import { writeFile } from 'fs/promises';
import { join } from 'path';
import { v4 as uuidv4 } from 'uuid';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return NextResponse.json(
        { error: 'No file uploaded' },
        { status: 400 }
      );
    }

    // Create a unique filename
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);
    const filename = `${uuidv4()}-${file.name}`;

    // Save the file in a shared uploads directory accessible by both frontend and backend
    const uploadDir = join(process.cwd(), '..', 'data', 'uploads');
    const filePath = join(uploadDir, filename);
    
    await writeFile(filePath, buffer);

    // Return the absolute file path for the uploaded file
    const absolutePath = filePath;
    
    return NextResponse.json({ url: absolutePath });
  } catch (error) {
    console.error('Error uploading file:', error);
    return NextResponse.json(
      { error: 'Error uploading file' },
      { status: 500 }
    );
  }
}
