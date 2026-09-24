from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from .models import Article, ArticleCategory, ArticleLibraryItem, ArticleAnnotation, ArticleTranslationVersion, ArticleSource
from accounts.models import User

class ArticleFlowTests(TestCase):
    def setUp(self):
        self.category=ArticleCategory.objects.create(name='Science',slug='science')
        self.article=Article.objects.create(title='Test Article',slug='test-article',category=self.category,published=True,full_text='Test article content')

    def test_published_article_is_visible(self):
        response=self.client.get(reverse('article_detail',args=[self.article.slug]))
        self.assertEqual(response.status_code,200)

    def test_unpublished_article_is_not_public(self):
        self.article.published=False; self.article.save(update_fields=['published'])
        response=self.client.get(reverse('article_detail',args=[self.article.slug]))
        self.assertEqual(response.status_code,404)

    def test_citation_export_is_available(self):
        response=self.client.get(reverse('article_citation_export',args=[self.article.slug])+'?format=bibtex')
        self.assertEqual(response.status_code,200)
        self.assertIn(b'@article', response.content)

    def test_authenticated_research_library_and_progress(self):
        user=User.objects.create_user(username='researcher',password='secret')
        self.client.force_login(user)
        response=self.client.get(reverse('article_library'))
        self.assertEqual(response.status_code,200)
        response=self.client.post(reverse('article_reading_progress',args=[self.article.slug]), {'progress':42,'position':180,'seconds':30})
        self.assertEqual(response.status_code,200)
        item=ArticleLibraryItem.objects.get(user=user,article=self.article)
        self.assertEqual(item.progress,42)
        self.assertEqual(item.status,'reading')

    def test_annotation_create_and_delete_are_owner_scoped(self):
        user=User.objects.create_user(username='annotator',password='secret')
        self.client.force_login(user)
        response=self.client.post(reverse('article_annotation_create',args=[self.article.slug]), {'selected_text':'important finding','kind':'highlight'})
        self.assertEqual(response.status_code,200)
        annotation=ArticleAnnotation.objects.get(user=user,article=self.article)
        response=self.client.post(reverse('article_annotation_delete',args=[annotation.pk]))
        self.assertEqual(response.status_code,200)
        self.assertFalse(ArticleAnnotation.objects.filter(pk=annotation.pk).exists())

    def test_pdf_reader_requires_pdf_and_redirects_cleanly(self):
        user=User.objects.create_user(username='pdfuser',password='secret')
        self.client.force_login(user)
        response=self.client.get(reverse('article_pdf_reader',args=[self.article.slug]))
        self.assertEqual(response.status_code,302)
        self.assertEqual(response.url,reverse('article_detail',args=[self.article.slug]))

    def test_pdf_annotation_persists_rects_and_color(self):
        user=User.objects.create_user(username='pdfannotator',password='secret')
        self.client.force_login(user)
        response=self.client.post(reverse('article_annotation_create',args=[self.article.slug]), {'selected_text':'PDF evidence','kind':'highlight','color':'blue','page':3,'rects':'[{"page":3,"x":0.1,"y":0.2,"w":0.3,"h":0.04}]'})
        self.assertEqual(response.status_code,200)
        item=ArticleAnnotation.objects.get(user=user,article=self.article)
        self.assertEqual(item.color,'blue')
        self.assertEqual(item.rects[0]['page'],3)
    def test_annotation_update_is_owner_scoped(self):
        user=User.objects.create_user(username='noteowner',password='secret')
        self.client.force_login(user)
        self.client.post(reverse('article_annotation_create',args=[self.article.slug]), {'selected_text':'quote','kind':'note'})
        annotation=ArticleAnnotation.objects.get(user=user,article=self.article)
        response=self.client.post(reverse('article_annotation_update',args=[annotation.pk]), {'note':'Research note','color':'green'})
        self.assertEqual(response.status_code,200)
        annotation.refresh_from_db()
        self.assertEqual(annotation.note,'Research note')
        self.assertEqual(annotation.color,'green')

    def test_bookmark_toggle_persists(self):
        user=User.objects.create_user(username='bookmarkuser',password='secret')
        self.client.force_login(user)
        response=self.client.post(reverse('article_bookmark_toggle',args=[self.article.slug]), {'page':7})
        self.assertEqual(response.status_code,200)
        item=ArticleLibraryItem.objects.get(user=user,article=self.article)
        self.assertEqual(item.bookmarks,[7])
        response=self.client.post(reverse('article_bookmark_toggle',args=[self.article.slug]), {'page':7})
        self.assertEqual(response.status_code,200)
        item.refresh_from_db()
        self.assertEqual(item.bookmarks,[])

    def test_annotation_rects_are_sanitized(self):
        user=User.objects.create_user(username='rectuser',password='secret')
        self.client.force_login(user)
        payload='[{"page":3,"x":-2,"y":2,"w":0.4,"h":0.02},{"page":"bad"},{"x":0,"y":0,"w":0,"h":0}]'
        response=self.client.post(reverse('article_annotation_create',args=[self.article.slug]), {'selected_text':'safe','rects':payload})
        self.assertEqual(response.status_code,200)
        annotation=ArticleAnnotation.objects.get(user=user,article=self.article)
        self.assertEqual(len(annotation.rects),1)
        self.assertEqual(annotation.rects[0]['x'],0)
        self.assertEqual(annotation.rects[0]['y'],1)


class TranslationHistoryTests(TestCase):
    def setUp(self):
        self.article = Article.objects.create(
            title='Original title', slug='translation-history',
            abstract='Original abstract', full_text='Original body', published=True,
        )

    def test_translation_creates_version_without_overwriting_original(self):
        from unittest.mock import patch
        from .translation import translate_article
        original = (self.article.title, self.article.abstract, self.article.full_text)
        with patch('articles.translation.translate_text', side_effect=['عنوان فارسی', 'چکیده فارسی', 'متن فارسی']):
            translate_article(self.article, full_text=True, force=True)
        self.article.refresh_from_db()
        self.assertEqual((self.article.title, self.article.abstract, self.article.full_text), original)
        self.assertEqual(self.article.full_text_fa, 'متن فارسی')
        self.assertEqual(self.article.translation_version, 1)
        self.assertEqual(self.article.translation_quality, 100)
        self.assertEqual(ArticleTranslationVersion.objects.filter(article=self.article).count(), 1)

    def test_failed_translation_keeps_previous_valid_persian_content(self):
        from unittest.mock import patch
        from .translation import translate_article
        self.article.title_fa = 'ترجمه سالم'
        self.article.full_text_fa = 'متن سالم'
        self.article.translation_version = 1
        self.article.save()
        with patch('articles.translation.translate_text', side_effect=RuntimeError('provider unavailable')):
            translate_article(self.article, full_text=True, force=True)
        self.article.refresh_from_db()
        self.assertEqual(self.article.title_fa, 'ترجمه سالم')
        self.assertEqual(self.article.full_text_fa, 'متن سالم')
        self.assertEqual(self.article.translation_status, 'provider_failed')
        self.assertIn('provider unavailable', self.article.translation_error)


class ArticleAdminTranslationTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser(username='article-admin', password='secret', email='admin@example.com')
        self.client.force_login(self.staff)
        self.article = Article.objects.create(title='Admin translation', slug='admin-translation', full_text='Body', published=True)

    def test_admin_can_rollback_to_previous_valid_translation(self):
        ArticleTranslationVersion.objects.create(article=self.article, version=1, title_fa='نسخه یک', content_fa='متن یک', source_hash='one')
        ArticleTranslationVersion.objects.create(article=self.article, version=2, title_fa='نسخه دو', content_fa='متن دو', source_hash='two')
        self.article.title_fa = 'نسخه دو'
        self.article.full_text_fa = 'متن دو'
        self.article.translation_version = 2
        self.article.translation_hash = 'two'
        self.article.save()
        response = self.client.post(
            reverse('admin:articles_article_changelist'),
            {'action': 'rollback_translation', '_selected_action': [self.article.pk]},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.article.refresh_from_db()
        self.assertEqual(self.article.translation_version, 3)
        self.assertEqual(self.article.full_text_fa, 'متن یک')
        rollback = self.article.translation_versions.get(version=3)
        self.assertEqual(rollback.provider, 'rollback')
        self.assertEqual(rollback.content_fa, 'متن یک')
        self.assertEqual(self.article.translation_status, 'reviewed')


class ArticleSourcePolicyTests(TestCase):
    def test_import_does_not_attach_pdf_when_full_republish_is_disabled(self):
        from unittest.mock import patch
        from .importer import import_discovered
        source=ArticleSource.objects.create(name='policy-provider',source_type='api',allow_full_republish=False)
        row={'provider':'policy-provider','external_id':'p1','title':'Policy paper','authors':'A','abstract':'Readable abstract','year':2026,'publication_date':None,'journal':'J','doi':'10.1/policy','source_url':'https://example.test/paper','pdf_url':'https://example.test/paper.pdf','citation_count':1,'relevance_score':1}
        with patch('articles.importer.discover_articles',return_value=[row]):
            import_discovered('policy')
        article=Article.objects.get(doi='10.1/policy')
        self.assertEqual(article.pdf_url,'')
        self.assertEqual(article.access,'external')
        self.assertEqual(article.source,source)


class ArticleFallbackTests(TestCase):
    def test_detail_defaults_to_original_when_persian_is_unavailable(self):
        article=Article.objects.create(title='Original only',slug='original-only',abstract='Original abstract',full_text='Original body',published=True)
        response=self.client.get(reverse('article_detail',args=[article.slug]))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['language_mode'],'en')
        self.assertContains(response,'Original body')


    def test_pdf_download_respects_source_republish_policy(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        source=ArticleSource.objects.create(name='restricted-download',source_type='manual',allow_full_republish=False)
        article=Article.objects.create(title='Restricted PDF',slug='restricted-pdf',published=True,source=source,pdf=SimpleUploadedFile('restricted.pdf',b'%PDF-1.4'))
        response=self.client.get(reverse('article_download',args=[article.slug]))
        self.assertEqual(response.status_code,403)


    def test_pdf_reader_respects_source_republish_policy(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        source=ArticleSource.objects.create(name='reader-restricted',source_type='manual',allow_full_republish=False)
        article=Article.objects.create(title='Reader Restricted',slug='reader-restricted',published=True,source=source,pdf=SimpleUploadedFile('reader.pdf',b'%PDF-1.4'))
        user=User.objects.create_user(username='pdf-policy-user',password='pass12345')
        self.client.force_login(user)
        response=self.client.get(reverse('article_pdf_reader',args=[article.slug]))
        self.assertRedirects(response,reverse('article_detail',args=[article.slug]))


    def test_article_search_matches_arabic_character_variant(self):
        Article.objects.create(title='دانش یک',slug='persian-article-search',published=True,abstract='Readable')
        response=self.client.get(reverse('article_list'),{'q':'دانش يك'})
        self.assertContains(response,'دانش یک')


    def test_restricted_source_detail_never_renders_full_text(self):
        source=ArticleSource.objects.create(name='restricted-detail',source_type='manual',allow_full_republish=False)
        article=Article.objects.create(title='Restricted body',slug='restricted-body',abstract='Public abstract',full_text='SECRET ORIGINAL BODY',full_text_fa='SECRET PERSIAN BODY',published=True,source=source,source_url='https://example.test/original')
        response=self.client.get(reverse('article_detail',args=[article.slug]),{'lang':'both'})
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.context['can_show_full_text'])
        self.assertNotContains(response,'SECRET ORIGINAL BODY')
        self.assertNotContains(response,'SECRET PERSIAN BODY')
        self.assertContains(response,'طبق سیاست منبع')


    def test_mostly_english_translation_candidate_is_rejected(self):
        from .translation import translate_article
        article=Article.objects.create(title='Machine learning systems',slug='quality-reject',title_fa='ترجمه سالم قبلی',translation_status='reviewed',translation_version=1,published=True)
        with patch('articles.translation.translate_text',return_value='مدل machine learning system performance results'):
            translate_article(article,force=True)
        article.refresh_from_db()
        self.assertEqual(article.title_fa,'ترجمه سالم قبلی')
        self.assertEqual(article.translation_version,1)
        self.assertEqual(article.translation_status,'validation_failed')


class ArticleDownloadSecurityTests(TestCase):
    def test_local_pdf_urls_are_rejected(self):
        from .translation import _safe_remote_url
        self.assertFalse(_safe_remote_url('http://127.0.0.1/private.pdf'))
        self.assertFalse(_safe_remote_url('http://localhost/private.pdf'))
        self.assertFalse(_safe_remote_url('file:///etc/passwd'))


class ArticleDiscoveryInputTests(TestCase):
    def test_invalid_sort_falls_back_to_top(self):
        Article.objects.create(title='Readable',slug='readable-sort',published=True,abstract='content')
        response=self.client.get(reverse('article_list'),{'sort':'invalid'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['selected_sort'],'top')


class ArticleRenderingSecurityTests(TestCase):
    def test_full_text_html_is_escaped(self):
        article=Article.objects.create(title='Unsafe HTML',slug='unsafe-html',published=True,full_text='<script>alert(1)</script>')
        response=self.client.get(reverse('article_detail',args=[article.slug]),{'lang':'en'})
        self.assertNotContains(response,'<script>alert(1)</script>',html=False)
        self.assertContains(response,'&lt;script&gt;alert(1)&lt;/script&gt;',html=False)


class ArticleSlugTests(TestCase):
    def test_duplicate_titles_receive_unique_slugs(self):
        first=Article.objects.create(title='عنوان تکراری')
        second=Article.objects.create(title='عنوان تکراری')
        self.assertNotEqual(first.slug,second.slug)
        self.assertTrue(second.slug.startswith(first.slug))


class ResearchLibrarySearchTests(TestCase):
    def test_library_search_normalizes_persian_letters(self):
        user=User.objects.create_user(username='researcher',password='pass12345')
        article=Article.objects.create(title='کتاب پژوهشی',published=True,abstract='متن')
        ArticleLibraryItem.objects.create(user=user,article=article)
        self.client.force_login(user)
        response=self.client.get(reverse('article_library'),{'q':'كتاب'})
        self.assertContains(response,'کتاب پژوهشی')


    def test_research_library_is_paginated(self):
        user=User.objects.create_user(username='library-pages',password='pass12345')
        for i in range(31):
            article=Article.objects.create(title=f'Article {i}',slug=f'article-lib-{i}',published=True,abstract='متن')
            ArticleLibraryItem.objects.create(user=user,article=article)
        self.client.force_login(user)
        response=self.client.get(reverse('article_library'))
        self.assertEqual(len(response.context['items']),30)
        second=self.client.get(reverse('article_library'),{'page':2})
        self.assertEqual(len(second.context['items']),1)


    def test_library_hides_unpublished_articles_and_annotations(self):
        user=User.objects.create_user(username='private-researcher',password='pass12345')
        article=Article.objects.create(title='Hidden research',slug='hidden-research',published=False,abstract='متن')
        ArticleLibraryItem.objects.create(user=user,article=article)
        ArticleAnnotation.objects.create(user=user,article=article,selected_text='secret')
        self.client.force_login(user)
        response=self.client.get(reverse('article_library'))
        self.assertNotContains(response,'Hidden research')
        self.assertNotContains(response,'secret')


class UnicodeArticleRouteTests(TestCase):
    def test_unicode_slug_detail_route_resolves(self):
        article=Article.objects.create(title='مقاله فارسی',published=True,abstract='متن')
        response=self.client.get(reverse('article_detail',args=[article.slug]))
        self.assertEqual(response.status_code,200)


class ArticleLanguageFallbackTests(TestCase):
    def test_english_mode_falls_back_to_available_persian_content(self):
        article=Article.objects.create(title='Persian only',slug='persian-only',published=True,abstract_fa='خلاصه فارسی')
        response=self.client.get(reverse('article_detail',args=[article.slug]),{'lang':'en'})
        self.assertEqual(response.context['language_mode'],'fa')


class TranslationPipelineRegressionTests(TestCase):
    @patch('articles.translation.time.sleep',return_value=None)
    @patch('articles.translation.requests.get')
    def test_translation_provider_retries_then_uses_success(self,get,sleep):
        from .translation import translate_text
        import requests
        success=type('Response',(),{'status_code':200,'raise_for_status':lambda self:None,'json':lambda self:{'responseData':{'translatedText':'ترجمه فارسی معتبر'}}})()
        get.side_effect=[requests.ConnectionError('temporary'),success]
        self.assertEqual(translate_text('research',retries=2),'ترجمه فارسی معتبر')
        self.assertEqual(get.call_count,2)

    @patch('articles.translation.time.sleep',return_value=None)
    @patch('articles.translation.requests.get')
    def test_free_fallback_is_used_when_provider_fails(self,get,sleep):
        from .translation import translate_text
        import requests
        get.side_effect=requests.ConnectionError('offline')
        result=translate_text('machine learning',retries=1)
        self.assertIn('یادگیری ماشین',result)

    def test_existing_failed_and_partial_articles_are_in_default_backlog(self):
        from django.core.management import call_command
        from io import StringIO
        failed=Article.objects.create(title='Failed source',slug='failed-backlog',abstract='Abstract',translation_status='failed',published=True)
        partial=Article.objects.create(title='Partial source',slug='partial-backlog',title_fa='عنوان فارسی',abstract='Needs translation',translation_status='translated',published=True)
        out,err=StringIO(),StringIO()
        with patch('articles.management.commands.translate_articles.translate_article') as translate:
            def healthy(article,**kwargs):
                article.translation_status='translated'
                article.translation_error=''
                return article
            translate.side_effect=healthy
            call_command('translate_articles',stdout=out,stderr=err)
        processed={call.args[0].pk for call in translate.call_args_list}
        self.assertIn(failed.pk,processed)
        self.assertIn(partial.pk,processed)

    def test_partial_candidate_never_replaces_healthy_translation(self):
        from .translation import translate_article
        article=Article.objects.create(title='Source title',slug='partial-candidate',abstract='Source abstract',title_fa='عنوان سالم',abstract_fa='چکیده سالم',translation_status='reviewed',translation_version=1,published=True)
        with patch('articles.translation.translate_text',side_effect=['عنوان جدید','English only abstract']):
            translate_article(article,force=True)
        article.refresh_from_db()
        self.assertEqual(article.title_fa,'عنوان سالم')
        self.assertEqual(article.abstract_fa,'چکیده سالم')
        self.assertEqual(article.translation_version,1)
        self.assertEqual(article.translation_status,'validation_failed')


class ArticleImporterTranslationTriggerTests(TestCase):
    def test_importer_triggers_translation_processing_for_existing_untranslated_article(self):
        from .importer import import_discovered
        row={'provider':'trigger-provider','external_id':'trigger-1','title':'Trigger paper','authors':'A','abstract':'Readable abstract','year':2026,'publication_date':None,'journal':'J','doi':'10.1/trigger','source_url':'https://example.test/paper','pdf_url':'','citation_count':1,'relevance_score':1}
        with patch('articles.importer.discover_articles',return_value=[row]), patch('articles.signals.schedule_article_processing') as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                import_discovered('trigger')
            article=Article.objects.get(doi='10.1/trigger')
            self.assertEqual(article.translation_status,'pending')
            schedule.assert_called_with(article.pk)


class ArticleCatalogSearchPerformanceTests(TestCase):
    def test_catalog_search_uses_metadata_and_abstract_without_full_body_scan(self):
        Article.objects.create(
            title='Metadata Needle', slug='metadata-needle', abstract='Readable summary',
            full_text='ordinary body', published=True,
        )
        Article.objects.create(
            title='Other Article', slug='body-only-needle', abstract='Readable summary',
            full_text='Metadata Needle appears only in this very large body', published=True,
        )
        response=self.client.get(reverse('article_list'), {'q':'Metadata Needle'})
        self.assertContains(response,'Metadata Needle')
        self.assertNotContains(response,'Other Article')


class ArticleFullTextCoverageRegressionTests(TestCase):
    def test_full_translation_fills_missing_body_even_when_metadata_hash_matches(self):
        import hashlib
        from .translation import translate_article
        article=Article.objects.create(
            title='Coverage source', slug='coverage-source', abstract='Source abstract',
            full_text='Source body requiring Persian translation',
            title_fa='عنوان موجود', abstract_fa='چکیده موجود',
            translation_status='translated', published=True,
        )
        source_hash=hashlib.sha256(
            f'{article.title}\n{article.abstract}\n{article.full_text}'.encode('utf-8')
        ).hexdigest()
        Article.objects.filter(pk=article.pk).update(translation_hash=source_hash)
        article.refresh_from_db()
        with patch('articles.translation.translate_text',return_value='متن فارسی کامل') as translate:
            result=translate_article(article,full_text=True)
        result.refresh_from_db()
        self.assertEqual(result.full_text_fa,'متن فارسی کامل')
        self.assertEqual(result.translation_status,'translated')
        self.assertEqual(translate.call_count,1)


class ArticleTranslationStateDisplayTests(TestCase):
    def test_failed_translation_keeps_original_and_explains_failure(self):
        article=Article.objects.create(title='Failed Persian',slug='failed-persian-display',abstract='English abstract remains readable',translation_status='failed',translation_error='provider unavailable',published=True)
        response=self.client.get(reverse('article_detail',args=[article.slug]),{'lang':'fa'})
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'ترجمه فارسی ناموفق بود؛ متن اصلی محفوظ است')
        self.assertContains(response,'English abstract remains readable')

    def test_pending_translation_keeps_original_available(self):
        article=Article.objects.create(title='Pending Persian',slug='pending-persian-display',abstract='Original content available',translation_status='pending',published=True)
        response=self.client.get(reverse('article_detail',args=[article.slug]),{'lang':'fa'})
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Original content available')


class AutomaticArticleProcessingRegressionTests(TestCase):
    def test_processing_article_without_pdf_url_still_translates(self):
        from articles.services import _process_article
        article=Article.objects.create(
            title='Abstract only processing', slug='abstract-only-processing',
            abstract='Readable abstract', published=True,
        )
        with patch('articles.services.translate_article') as translate:
            translate.return_value=type('Result',(),{'translation_status':'translated','translation_error':''})()
            _process_article(article.pk)
        translate.assert_called_once()
        self.assertFalse(translate.call_args.kwargs['full_text'])


class ArticleProcessingSignalRegressionTests(TestCase):
    def test_internal_translation_status_save_does_not_requeue_processing(self):
        article=Article.objects.create(title='Signal guard',slug='signal-guard',abstract='Readable',published=False)
        article.published=True
        with patch('articles.signals.schedule_article_processing') as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                article.save(update_fields=['published'])
            self.assertEqual(schedule.call_count,1)
            schedule.reset_mock()
            with self.captureOnCommitCallbacks(execute=True):
                Article.objects.filter(pk=article.pk).update(translation_status='translating')
            schedule.assert_not_called()

    def test_source_text_update_requeues_processing(self):
        article=Article.objects.create(title='Signal source',slug='signal-source',abstract='Readable',published=False)
        Article.objects.filter(pk=article.pk).update(published=True)
        article.refresh_from_db()
        with patch('articles.signals.schedule_article_processing') as schedule:
            article.abstract='Updated readable abstract'
            with self.captureOnCommitCallbacks(execute=True):
                article.save(update_fields=['abstract'])
            schedule.assert_called_once_with(article.pk)


class RestrictedSourceTranslationRegressionTests(TestCase):
    def test_restricted_source_still_translates_metadata_without_full_republish(self):
        from articles.services import _process_article
        source=ArticleSource.objects.create(name='Restricted source',source_type='api',allow_full_republish=False)
        article=Article.objects.create(title='Restricted article',slug='restricted-article',abstract='Readable abstract',source=source,published=True)
        with patch('articles.services.translate_article') as translate:
            translate.return_value=type('Result',(),{'translation_status':'translated','translation_error':''})()
            _process_article(article.pk)
        translate.assert_called_once()
        self.assertFalse(translate.call_args.kwargs['full_text'])


class LegacyDownloaderSecurityRegressionTests(TestCase):
    @patch('articles.translation.socket.getaddrinfo', return_value=[(None,None,None,None,('127.0.0.1',80))])
    @patch('articles.translation.requests.get')
    def test_legacy_downloader_rejects_private_network_target(self, get, _dns):
        from articles.downloader import download_pdf
        article=Article.objects.create(title='SSRF guard',slug='ssrf-guard',pdf_url='http://internal.example/private.pdf',published=True)
        with self.assertRaises(ValueError):
            download_pdf(article)
        get.assert_not_called()


class TranslationFailureClassificationTests(TestCase):
    @patch('articles.translation.translate_text', return_value='english only result')
    def test_quality_failure_is_not_marked_translated(self, _translate):
        from articles.translation import translate_article
        article=Article.objects.create(title='Quality source',slug='quality-source',abstract='Useful source abstract',published=True)
        result=translate_article(article)
        self.assertEqual(result.translation_status,'validation_failed')
        self.assertNotEqual(result.translation_status,'translated')
        self.assertEqual(result.translation_version,0)
