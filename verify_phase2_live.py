"""Opt-in Phase 2 browser/API regression against the running local app.

Usage: python verify_phase2_live.py --browser-session SESSION_ID
Creates uniquely named temporary catalog fixtures, never modifies existing books
or users, and removes only its own fixtures. Tokens stay in process memory.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import uuid

import httpx
from app.database import SessionLocal, engine
from app.models.library import Library
from app.models.user import User, UserRole
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.models.review import Review
from app.models.digital_resource import DigitalResource
from app.services.auth import create_access_token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser-session', required=True)
    args = parser.parse_args()
    marker = 'Phase2 QA ' + uuid.uuid4().hex[:12]
    ids = []
    resource_id = None
    assert engine.url.database == 'bookbridge_v2'
    with SessionLocal() as db:
        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        staff = db.query(User).filter(User.role == UserRole.LIBRARIAN).first()
        assert student and staff
        student_token = create_access_token(student.id, student.role.value)
        staff_token = create_access_token(staff.id, staff.role.value)
        student_id, staff_id = student.id, staff.id
        library = db.query(Library).first()
        assert library
        library_id = library.id
        before_books = db.query(Book).count()
    try:
        with SessionLocal() as db:
            for label in ('Available', 'Queued', 'Cancel'):
                book = Book(title=f'{marker} {label}', author='Phase 2 verification',
                            category=marker, total_copies=1,
                            available_copies=1 if label == 'Available' else 0,
                            library_id=library_id, publication_year=2024)
                db.add(book)
                db.flush()
                ids.append(book.id)
                if label != 'Available':
                    db.add(BorrowRecord(user_id=staff_id, book_id=book.id,
                        due_date=datetime.now(timezone.utc) + timedelta(days=14), status='borrowed'))
            resource = DigitalResource(title=f'{marker} Available', author='Phase 2 verification',
                resource_type='uploaded_pdf', access_type='free', provider='Verification document',
                library_id=library_id, uploaded_by=staff_id,
                file_url='/uploads/real_test_document.pdf', is_published=True)
            db.add(resource)
            db.flush()
            resource_id = resource.id
            db.commit()
        with httpx.Client(base_url='http://127.0.0.1:8000', timeout=20) as client:
            result = client.get(f'/books/{ids[0]}')
            assert result.status_code == 200
            assert result.json()['publication_year'] == 2024
            assert result.json()['library_id'] == library_id
            assert 'cover_image' in result.json()
        program = r"""
const errors = [];
page.on('pageerror', error => errors.push(error.message));
await page.goto('http://127.0.0.1:5173/login');
await page.evaluate(token => localStorage.setItem('bookbridge_token', token), TOKEN);
await page.goto('http://127.0.0.1:5173/books?search=' + encodeURIComponent(MARKER));
await page.locator('[data-book-id="'+IDS[0]+'"]').waitFor();
if (await page.getByRole('textbox',{name:'Search catalog',exact:true}).inputValue() !== MARKER) throw new Error('URL search not restored');
if (await page.locator('[data-book-id]').count() !== 3) throw new Error('Catalog filter failed');
await page.getByRole('checkbox',{name:'Available now'}).check();
if (await page.locator('[data-book-id]').count() !== 1) throw new Error('Availability filter failed');
await page.reload();
await page.locator('[data-book-id="'+IDS[0]+'"]').waitFor();
if (!(await page.getByRole('checkbox',{name:'Available now'}).isChecked())) throw new Error('Filter lost on reload');
await page.getByRole('checkbox',{name:'Available now'}).uncheck();
await page.getByRole('textbox',{name:'Search library catalog',exact:true}).fill(MARKER+' Available');
await page.getByRole('textbox',{name:'Search library catalog',exact:true}).press('Enter');
await page.locator('[data-book-id="'+IDS[0]+'"]').getByRole('link',{name:'Details',exact:true}).click();
await page.getByRole('heading',{name:MARKER+' Available',exact:true}).waitFor();
await page.getByText('Not rated yet',{exact:true}).waitFor();
await page.getByText('2024',{exact:true}).waitFor();
await page.getByRole('link',{name:'Read digital edition · Verification document',exact:true}).waitFor();
await page.getByRole('region',{name:'Similar books'}).waitFor();
const borrowPending = page.waitForResponse(r=>r.url().endsWith('/borrows/') && r.request().method()==='POST');
await page.getByRole('button',{name:'Borrow',exact:true}).click();
const borrowed = await borrowPending;
if (borrowed.status() !== 201) throw new Error('Borrow failed');
const loan = await borrowed.json();
await page.getByRole('button',{name:'Already borrowed',exact:true}).waitFor();
if (!(await page.getByRole('button',{name:'Already borrowed',exact:true}).isDisabled())) throw new Error('Duplicate borrow enabled');
await page.getByRole('button',{name:'Rate 4 stars',exact:true}).click();
await page.getByLabel('Your Comments',{exact:true}).fill('Useful verification book.');
await page.getByRole('button',{name:'Post Review',exact:true}).click();
await page.getByText('4.0',{exact:true}).waitFor();
await page.goto('http://127.0.0.1:5173/my-books');
await page.locator('[data-borrow-id="'+loan.id+'"]').getByRole('button',{name:'Return Book',exact:true}).click();
await page.getByRole('status').filter({hasText:'Successfully returned'}).waitFor();
await page.getByRole('button',{name:/Returned history/}).click();
await page.getByRole('main').getByRole('link',{name:MARKER+' Available',exact:true}).waitFor();
await page.reload();
await page.getByRole('heading',{name:'Returned books',exact:true}).waitFor();
await page.goto('http://127.0.0.1:5173/books?search='+encodeURIComponent(MARKER+' Cancel'));
const cancelPending=page.waitForResponse(r=>r.url().endsWith('/reservations/')&&r.request().method()==='POST');
await page.getByRole('button',{name:'Reserve: '+MARKER+' Cancel',exact:true}).click();
const cancelResponse=await cancelPending;
if(cancelResponse.status()!==201)throw new Error('Reserve failed');
const cancelReservation=await cancelResponse.json();
await page.goto('http://127.0.0.1:5173/my-books?tab=reservations');
await page.locator('[data-reservation-id="'+cancelReservation.id+'"]').getByRole('button',{name:'Cancel reservation',exact:true}).click();
await page.getByRole('status').filter({hasText:'Reservation cancelled'}).waitFor();
await page.goto('http://127.0.0.1:5173/books/'+IDS[1]);
const reservePending=page.waitForResponse(r=>r.url().endsWith('/reservations/')&&r.request().method()==='POST');
await page.getByRole('button',{name:'Reserve',exact:true}).click();
const reserved=await reservePending;
if(reserved.status()!==201)throw new Error('Details reserve failed');
const reservation=await reserved.json();
await page.getByRole('button',{name:'Reserved',exact:true}).waitFor();
// Release only the test fixture's staff loan through the existing API.
const staffLoans=await page.request.get('http://127.0.0.1:8000/borrows/my',{headers:{Authorization:'Bearer '+STAFF_TOKEN}});
const heldLoan=(await staffLoans.json()).find(item=>item.book_id===IDS[1]&&item.status==='borrowed');
const returned=await page.request.post('http://127.0.0.1:8000/borrows/'+heldLoan.id+'/return',{headers:{Authorization:'Bearer '+STAFF_TOKEN}});
if(returned.status()!==200)throw new Error('Queue release failed');
await page.goto('http://127.0.0.1:5173/my-books?tab=reservations');
await page.locator('[data-reservation-id="'+reservation.id+'"]').getByRole('button',{name:'Borrow reserved copy',exact:true}).click();
await page.getByRole('status').filter({hasText:'Reserved copy borrowed'}).waitFor();
await page.goto('http://127.0.0.1:5173/reviews');
await page.getByRole('heading',{name:'Book Reviews',exact:true}).waitFor();
await page.setViewportSize({width:390,height:844});
await page.getByRole('button',{name:'Open navigation',exact:true}).click();
await page.getByRole('navigation').getByRole('link',{name:'My Library',exact:true}).click();
await page.getByRole('heading',{name:'My Library',exact:true}).waitFor();
const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
if(overflow)throw new Error('Mobile horizontal overflow');
await page.setViewportSize({width:1440,height:1000});
await page.goto('http://127.0.0.1:5173/books/999999999');
await page.getByRole('heading',{name:'Book unavailable',exact:true}).waitFor();
await page.goto('http://127.0.0.1:5173/books/'+IDS[0]);
await page.getByRole('heading',{name:MARKER+' Available',exact:true}).waitFor();
if(errors.length)throw new Error('Page errors: '+errors.join('; '));
return {urlSearch:true,availabilityFilter:true,reload:true,headerSearch:true,realMetadata:true,
  unratedState:true,digitalLink:true,similarBooks:true,borrow:true,return:true,returnedHistory:true,
  review:true,reserve:true,cancel:true,heldCopyCheckout:true,reviewsNavigation:true,mobile:true,
  missingBookRecovery:true,pageErrors:errors};
"""
        constants = '\n'.join(f'const {key} = {json.dumps(value)};' for key, value in {
            'TOKEN': student_token, 'STAFF_TOKEN': staff_token, 'MARKER': marker, 'IDS': ids,
        }.items())
        command = [str(Path.home()/'AppData/Roaming/npm/webcmd.cmd'), '--profile','bookbridge-notes',
                   '--session',args.browser_session,'browser','run','--stdin','--timeout','55','--no-snapshot-diff']
        result = subprocess.run(command,input=constants+program,text=True,capture_output=True,encoding='utf-8',timeout=65)
        output = (result.stdout+result.stderr).replace(student_token,'[redacted]').replace(staff_token,'[redacted]')
        if result.returncode: raise AssertionError(output[:5000])
        print(output)
        with SessionLocal() as db:
            assert db.query(Review).filter(Review.book_id==ids[0],Review.user_id==student_id).one().rating==4
            assert db.query(BorrowRecord).filter(BorrowRecord.book_id==ids[0],BorrowRecord.user_id==student_id).one().status=='returned'
            assert db.get(Book,ids[0]).available_copies==1
            assert db.get(Book,ids[1]).available_copies==0
            assert db.query(BorrowRecord).filter(BorrowRecord.book_id==ids[1],BorrowRecord.user_id==student_id).one().status=='borrowed'
            assert db.query(Reservation).filter(Reservation.book_id==ids[2],Reservation.user_id==student_id).one().status=='cancelled'
            print('PostgreSQL review, return, queue checkout and inventory checks passed.')
    finally:
        with SessionLocal() as db:
            if resource_id is not None:
                db.query(DigitalResource).filter(DigitalResource.id==resource_id).delete()
            for model in (Review, Reservation, BorrowRecord):
                db.query(model).filter(model.book_id.in_(ids)).delete(synchronize_session=False)
            db.query(Book).filter(Book.id.in_(ids),Book.title.like(marker+'%')).delete(synchronize_session=False)
            db.commit()
            assert db.query(Book).count()==before_books
        print('Temporary fixtures removed; existing books and users preserved.')

if __name__=='__main__':
    main()
