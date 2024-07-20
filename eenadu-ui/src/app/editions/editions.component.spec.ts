import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EditionsComponent } from './editions.component';

describe('EditionsComponent', () => {
  let component: EditionsComponent;
  let fixture: ComponentFixture<EditionsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditionsComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(EditionsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
