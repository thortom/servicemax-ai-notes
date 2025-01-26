import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { PlusCircle, Plus, Upload } from "lucide-react";
import { Resource } from "@/lib/types";
import { useState } from "react";

type AddResourceDialogProps = {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  newResource: Resource;
  setNewResource: (resource: Resource) => void;
  addResource: () => void;
};

export function AddResourceDialog({
  isOpen,
  onOpenChange,
  newResource,
  setNewResource,
  addResource,
}: AddResourceDialogProps) {
  const [resourceType, setResourceType] = useState<'url' | 'file'>('file');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setNewResource({
        ...newResource,
        file,
        url: undefined,
        title: file.name,
      });
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button
          variant="link"
          size="sm"
          className="text-sm font-bold text-[#6766FC]"
        >
          Add Resource <PlusCircle className="w-6 h-6 ml-2" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Add New Resource</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="flex gap-4">
            <Button
              variant={resourceType === 'url' ? "default" : "outline"}
              onClick={() => setResourceType('url')}
              className="flex-1"
            >
              URL
            </Button>
            <Button
              variant={resourceType === 'file' ? "default" : "outline"}
              onClick={() => setResourceType('file')}
              className="flex-1"
            >
              File Upload
            </Button>
          </div>

          {resourceType === 'url' ? (
            <>
              <label htmlFor="new-url" className="text-sm font-bold">
                Resource URL
              </label>
              <Input
                id="new-url"
                placeholder="Resource URL"
                value={newResource.url || ""}
                onChange={(e) =>
                  setNewResource({ ...newResource, url: e.target.value, file: undefined })
                }
                aria-label="New resource URL"
                className="bg-background"
              />
            </>
          ) : (
            <>
              <label htmlFor="new-file" className="text-sm font-bold">
                Upload File
              </label>
              <div className="flex items-center gap-2">
                <Input
                  id="new-file"
                  type="file"
                  onChange={handleFileChange}
                  aria-label="Upload file"
                  className="bg-background"
                />
              </div>
            </>
          )}

          <label htmlFor="new-title" className="text-sm font-bold">
            Resource Title
          </label>
          <Input
            id="new-title"
            placeholder="Resource Title"
            value={newResource.title || ""}
            onChange={(e) =>
              setNewResource({ ...newResource, title: e.target.value })
            }
            aria-label="New resource title"
            className="bg-background"
          />
        </div>
        <DialogFooter>
          <Button
            onClick={addResource}
            className="w-full bg-[#6766FC] text-white"
            disabled={
              (!newResource.url && !newResource.file) || !newResource.title
            }
          >
            <Plus className="w-4 h-4 mr-2" /> Add Resource
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
