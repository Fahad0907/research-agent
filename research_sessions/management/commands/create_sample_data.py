"""
Management command to create sample research sessions.
Run with: python manage.py create_sample_data
"""
from django.core.management.base import BaseCommand
from research_sessions.services import ResearchService


class Command(BaseCommand):
    help = 'Create sample research sessions with real repositories'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating sample research sessions...'))
        
        # Sample questions for FastAPI
        fastapi_samples = [
            {
                'repo_url': 'https://github.com/tiangolo/fastapi',
                'question': 'How does FastAPI handle dependency injection internally?'
            }
        ]
        
        # Sample questions for a smaller repo (requests library)
        requests_samples = [
            {
                'repo_url': 'https://github.com/psf/requests',
                'question': 'How does the requests library handle HTTP retries?'
            }
        ]
        
        samples = fastapi_samples + requests_samples
        
        for idx, sample in enumerate(samples, 1):
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Creating session {idx}/{len(samples)}")
            self.stdout.write(f"Repository: {sample['repo_url']}")
            self.stdout.write(f"Question: {sample['question']}")
            self.stdout.write('='*60)
            
            try:
                result = ResearchService.start_research(
                    repo_url=sample['repo_url'],
                    question=sample['question']
                )
                
                self.stdout.write(self.style.SUCCESS(f"✓ Session created: #{result['session_id']}"))
                self.stdout.write(f"Status: {result['status']}")
                self.stdout.write(f"Iterations: {result['metadata']['total_iterations']}")
                self.stdout.write(f"Tool calls: {result['metadata']['total_tool_calls']}")
                self.stdout.write(f"\nAnswer preview: {result['answer'][:200]}...")
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Failed: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS('\n\nSample data creation completed!'))
        self.stdout.write('You can now view sessions via API or Django admin.')
